#!/usr/bin/env python3
"""
Run:ai 監看工具（只用 Python 內建函式庫）

記錄「所有人」的 workload：誰、什麼時候開始/停掉、佔幾張 GPU、GPU 實際有沒有在用。
Discord 只通知「你自己的」workload 狀態變化。

環境變數: RUNAI_URL, RUNAI_USER, RUNAI_PASS, DISCORD_WEBHOOK, (選用) RUNAI_TOKEN

指令:
  watch.bat                      持續監看（記錄所有人 + 通知自己）
  watch.bat --once               現在所有人誰在跑、GPU 使用率多少
  watch.bat --history            所有人的開始/停止紀錄（最近 50 筆）
  watch.bat --history 200 --user eric   只看名字含 eric 的
  watch.bat --usage              每個人的 GPU 時數、平均使用率、閒置比例
  watch.bat --usage --days 1     只統計最近 1 天
"""
import argparse, csv, json, os, ssl, sys, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone, timedelta

p = argparse.ArgumentParser()
p.add_argument("--once", action="store_true")
p.add_argument("--history", nargs="?", const=50, type=int, metavar="N")
p.add_argument("--usage", action="store_true")
p.add_argument("--user", default="", help="篩選使用者（部分名稱即可）")
p.add_argument("--days", type=float, default=0, help="--usage 只統計最近幾天")
p.add_argument("--interval", type=int, default=60, help="檢查狀態的秒數")
p.add_argument("--snap", type=int, default=300, help="記錄 GPU 使用率的秒數")
p.add_argument("--insecure", action="store_true")
p.add_argument("--debug", action="store_true")
p.add_argument("--log", default=os.path.expanduser("~/runai_history.csv"))
args = p.parse_args()
USAGE_LOG = os.path.join(os.path.dirname(os.path.abspath(args.log)), "runai_usage.csv")

HIST_FIELDS = ["time", "user", "name", "project", "from", "to", "gpu", "ran_min", "waited_min"]
USE_FIELDS = ["time", "user", "name", "project", "gpu", "gpu_util", "gpu_mem_gb", "running_min", "snap_min"]


def short(u):
    return str(u or "?").split("@")[0]


def append(path, fields, row):
    first = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if first:
            w.writerow(fields)
        w.writerow(row)


def read(path):
    if not os.path.exists(path):
        sys.exit(f"還沒有紀錄：{path}（先讓 watch.bat 跑一陣子）")
    return list(csv.DictReader(open(path, encoding="utf-8")))


# ---------- 離線查詢（不用登入） ----------
if args.history is not None:
    rows = [r for r in read(args.log) if args.user.lower() in r["user"].lower()][-args.history:]
    print(f"{'時間':<20}{'使用者':<20}{'workload':<28}{'變化':<24}{'GPU':<5}{'跑了(分)':<10}{'等了(分)'}")
    for r in rows:
        chg = f"{r['from'] or '新建'} → {r['to']}"
        print(f"{r['time']:<20}{r['user']:<20}{r['name']:<28}{chg:<24}{r['gpu']:<5}{r['ran_min']:<10}{r['waited_min']}")
    sys.exit(0)

if args.usage:
    rows = read(USAGE_LOG)
    if args.days:
        cut = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d %H:%M:%S")
        rows = [r for r in rows if r["time"] >= cut]
    stat = {}
    for r in rows:
        if args.user.lower() not in r["user"].lower():
            continue
        s = stat.setdefault(r["user"], {"gh": 0.0, "u": [], "idle": 0, "n": 0, "jobs": set()})
        try:
            g = float(r["gpu"])
        except ValueError:
            g = 0
        s["gh"] += g * float(r["snap_min"] or 0) / 60
        s["n"] += 1
        s["jobs"].add(r["name"])
        if r["gpu_util"] != "":
            u = float(r["gpu_util"])
            s["u"].append(u)
            if u < 5:
                s["idle"] += 1
    print(f"{'使用者':<22}{'GPU小時':<10}{'平均使用率':<12}{'閒置比例(<5%)':<16}{'workload數'}")
    for user, s in sorted(stat.items(), key=lambda x: -x[1]["gh"]):
        avg = f"{sum(s['u'])/len(s['u']):.1f}%" if s["u"] else "無資料"
        idle = f"{s['idle']/len(s['u'])*100:.0f}%" if s["u"] else "-"
        print(f"{user:<22}{s['gh']:<10.1f}{avg:<12}{idle:<16}{len(s['jobs'])}")
    sys.exit(0)

# ---------- 連線 ----------
URL = os.environ.get("RUNAI_URL", "").rstrip("/")
USER = os.environ.get("RUNAI_USER", "")
PASS = os.environ.get("RUNAI_PASS", "")
HOOK = os.environ.get("DISCORD_WEBHOOK", "")
if not URL:
    sys.exit("請設定 RUNAI_URL")
CTX = ssl._create_unverified_context() if args.insecure else None


def http(method, url, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
        t = r.read().decode()
        return json.loads(t) if t else {}


def login():
    if os.environ.get("RUNAI_TOKEN"):
        return os.environ["RUNAI_TOKEN"]
    body = {"grantType": "password", "username": USER, "password": PASS}
    last = None
    for path in ("/api/v1/token", "/api/v2/token"):
        try:
            r = http("POST", URL + path, body)
            tok = r.get("accessToken") or r.get("access_token")
            if tok:
                return tok
        except urllib.error.HTTPError as e:
            last = f"{path}: HTTP {e.code} {e.read().decode()[:200]}"
    sys.exit(f"登入失敗\n{last}")


def discord(msg):
    print(msg, flush=True)
    if not HOOK:
        return
    try:
        req = urllib.request.Request(HOOK, data=json.dumps({"content": msg}).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "runai-watch"})
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"[discord 失敗] {e}", flush=True)


def fetch_all(token):
    out, off = {}, 0
    while True:
        r = http("GET", f"{URL}/api/v1/workloads?limit=500&offset={off}", token=token)
        wl = r.get("workloads", [])
        for w in wl:
            out[w.get("id") or w.get("workloadId") or w.get("name")] = w
        if len(wl) < 500:
            return out
        off += 500


def _gpu_num(x):
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return None
    if isinstance(x, dict):
        for k in ("request", "devices", "limit", "portion"):
            v = _gpu_num(x.get(k))
            if v:
                return v
    return None


def gpus(w):
    for src in ("allocatedResources", "workloadRequestedResources"):
        v = _gpu_num((w.get(src) or {}).get("gpu"))
        if v:
            return int(v) if float(v).is_integer() else v
    return "?"


def parse_t(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def minutes_since(s):
    t = parse_t(s)
    return round((datetime.now(timezone.utc) - t).total_seconds() / 60, 1) if t else ""


def _values(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "value":
                try:
                    yield float(v)
                except (TypeError, ValueError):
                    pass
            else:
                yield from _values(v)
    elif isinstance(o, list):
        for i in o:
            yield from _values(i)


_metric_warned = False


def metric(token, wid, mtype, minutes=5):
    global _metric_warned
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    q = urllib.parse.urlencode({"metricType": mtype,
                                "start": start.isoformat().replace("+00:00", "Z"),
                                "end": end.isoformat().replace("+00:00", "Z")})
    try:
        r = http("GET", f"{URL}/api/v1/workloads/{wid}/metrics?{q}", token=token)
    except Exception as e:
        if not _metric_warned or args.debug:
            print(f"[抓 {mtype} 失敗] {e}", flush=True)
            _metric_warned = True
        return ""
    if args.debug:
        print(f"[{mtype} 原始資料]", json.dumps(r, ensure_ascii=False)[:800])
    v = list(_values(r))
    return round(sum(v) / len(v), 1) if v else ""


def mem_gb(token, wid):
    v = metric(token, wid, "GPU_MEMORY_USAGE_BYTES")
    return round(v / 1e9, 1) if v != "" else ""


def cut(s, n):
    s = str(s)
    return s if len(s) < n else s[:n - 2] + "…"


def is_mine(w):
    return bool(USER) and short(USER).lower() in str(w.get("submittedBy", "")).lower()


def show(token, wl):
    run = [w for w in wl.values() if w.get("phase") == "Running"]
    pend = [w for w in wl.values() if w.get("phase") == "Pending"]
    tot = sum(float(gpus(w)) for w in run if str(gpus(w)).replace(".", "").isdigit())
    print(f"\n=== {time.strftime('%m/%d %H:%M')}  Running {len(run)} 個（共 {tot:g} GPU），Pending {len(pend)} 個 ===")
    print(f"{'使用者':<20}{'workload':<36}{'GPU':<5}{'使用率':<9}{'顯存GB':<9}{'已跑(時)'}")
    for w in sorted(run, key=lambda x: short(x.get("submittedBy"))):
        if args.user and args.user.lower() not in str(w.get("submittedBy", "")).lower():
            continue
        u = metric(token, w["id"], "GPU_UTILIZATION")
        m = mem_gb(token, w["id"])
        h = minutes_since(w.get("phaseUpdatedAt"))
        h = f"{h/60:.1f}" if h != "" else "?"
        flag = "  ← 閒置?" if u != "" and u < 5 else ""
        print(f"{cut(short(w.get('submittedBy')),20):<20}{cut(w.get('name','?'),36):<36}{str(gpus(w)):<5}"
              f"{(str(u)+'%') if u!='' else '-':<9}{str(m) if m!='' else '-':<9}{h}{flag}")
    if pend:
        print("\nPending:")
        for w in pend:
            print(f"  {cut(short(w.get('submittedBy')),20):<20}{cut(w.get('name','?'),36):<36}GPU:{gpus(w):<4} 已等 {minutes_since(w.get('phaseUpdatedAt'))} 分")


def snapshot(token, wl, snap_min):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for w in wl.values():
        if w.get("phase") != "Running":
            continue
        append(USAGE_LOG, USE_FIELDS, [now, short(w.get("submittedBy")), w.get("name"), w.get("projectName"),
                                       gpus(w), metric(token, w["id"], "GPU_UTILIZATION"),
                                       mem_gb(token, w["id"]),
                                       minutes_since(w.get("phaseUpdatedAt")), snap_min])


def log_change(w, old, new, prev_w=None):
    ran = waited = ""
    ref = prev_w or w
    if old == "Running":
        ran = minutes_since(ref.get("phaseUpdatedAt"))
    if old == "Pending":
        waited = minutes_since(ref.get("phaseUpdatedAt"))
    append(args.log, HIST_FIELDS, [time.strftime("%Y-%m-%d %H:%M:%S"), short(w.get("submittedBy")),
                                   w.get("name"), w.get("projectName"), old or "", new, gpus(w), ran, waited])
    return ran, waited


# ---------- 主程式 ----------
token, token_t = login(), time.time()
if args.once:
    show(token, fetch_all(token))
    sys.exit(0)

prev, last_snap = None, 0
while True:
    try:
        if time.time() - token_t > 1800 and not os.environ.get("RUNAI_TOKEN"):
            token, token_t = login(), time.time()
        cur = fetch_all(token)
    except urllib.error.HTTPError as e:
        if e.code == 401 and not os.environ.get("RUNAI_TOKEN"):
            token, token_t = login(), time.time()
            continue
        print(f"[HTTP {e.code}] {e.read().decode()[:200]}", flush=True)
        time.sleep(args.interval)
        continue
    except Exception as e:
        print(f"[錯誤] {e}", flush=True)
        time.sleep(args.interval)
        continue

    if prev is None:
        for w in cur.values():
            log_change(w, "(開始監看)", w.get("phase"))
        mine_p = [w["name"] for w in cur.values() if is_mine(w) and w.get("phase") == "Pending"]
        run = sum(1 for w in cur.values() if w.get("phase") == "Running")
        discord(f"👀 開始監看：全部 {len(cur)} 個 workload，Running {run} 個"
                + (f"；你 Pending 中: {', '.join(mine_p)}" if mine_p else ""))
    else:
        for k, w in cur.items():
            old, new = prev.get(k, {}).get("phase"), w.get("phase")
            if old == new:
                continue
            ran, waited = log_change(w, old, new, prev.get(k))
            print(f"[{time.strftime('%H:%M')}] {short(w.get('submittedBy'))} {w.get('name')}: {old} → {new}", flush=True)
            if not is_mine(w):
                continue
            name = w.get("name", k)
            if new == "Running":
                discord(f"🟢 **{name}** 等到 GPU 了！（GPU: {gpus(w)}" + (f"，等了 {waited} 分" if waited != "" else "") + "）")
            elif new in ("Failed", "Degraded"):
                discord(f"🔴 **{name}** {old} → {new}")
            elif new in ("Completed", "Succeeded"):
                discord(f"✅ **{name}** 跑完了" + (f"（跑了 {ran} 分）" if ran != "" else ""))
            else:
                discord(f"🔄 **{name}** {old or '新建'} → {new}")
        for k in prev.keys() - cur.keys():
            w = prev[k]
            ran, _ = log_change(w, w.get("phase"), "Deleted", w)
            print(f"[{time.strftime('%H:%M')}] {short(w.get('submittedBy'))} {w.get('name')}: 被刪除", flush=True)
            if is_mine(w):
                discord(f"🗑️ **{w.get('name')}** 已被刪除")

    if time.time() - last_snap >= args.snap:
        snapshot(token, cur, round(args.snap / 60, 2))
        last_snap = time.time()
    prev = cur
    time.sleep(args.interval)
