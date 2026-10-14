#!/usr/bin/env python3
# 佔住這台機器上所有看得到的 GPU（每張約 90% 顯存、約 13% 使用率）
# 啟動: nohup python3 gpu_hold_all.py > hold.log 2>&1 &
# 停止: kill $(cat ~/.gpu_hold.pid)
import os, signal, sys, time
import torch

PIDFILE = os.path.expanduser("~/.gpu_hold.pid")
open(PIDFILE, "w").write(str(os.getpid()))


def cleanup(*_):
    if os.path.exists(PIDFILE):
        os.remove(PIDFILE)
    print("[gpu_hold] released", flush=True)
    sys.exit(0)


signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

devs = list(range(torch.cuda.device_count()))
mats, blocks = [], []
for d in devs:
    torch.cuda.set_device(d)
    a = torch.randn(4096, 4096, device=d, dtype=torch.float16)
    b = torch.randn(4096, 4096, device=d, dtype=torch.float16)
    mats.append((d, a, b))
    free, _ = torch.cuda.mem_get_info(d)
    blocks.append(torch.empty(int(free * 0.9), dtype=torch.uint8, device=d))
    print(f"[gpu_hold] GPU {d}: holding {blocks[-1].numel() / 1e9:.1f} GB", flush=True)

while True:
    for d, a, b in mats:
        torch.cuda.set_device(d)
        for _ in range(15):
            torch.matmul(a, b)
    for d in devs:
        torch.cuda.synchronize(d)
    time.sleep(1)
