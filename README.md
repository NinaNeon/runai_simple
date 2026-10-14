# runai_simple
簡單常用的runai指令
## 步驟 3：建立 Environment

點 Assets → Environments → + NEW ENVIRONMENT，照 README 填：

- **Scope：** 選你的 project
- **Name：** `ken-wafercap`
- **Type：** 只勾 Workspace
- **Image：** `j3soon/runai-pytorch-mnist`
- **Pull policy：** Always pull
- **Tools：** Jupyter

**Command：**

```bash
/run.sh "pip install jupyterlab" "jupyter lab --ip=0.0.0.0 --no-browser --allow-root --NotebookApp.base_url=/${RUNAI_PROJECT}/${RUNAI_JOB_NAME} --NotebookApp.token='' --notebook-dir=/"
```

用系統管理員身分開 cmd（開始選單搜尋 cmd → 右鍵 →「以系統管理員身分執行」），執行：


```bash
echo 10.225.0.59 runai.tpe1.local >> C:\Windows\System32\drivers\etc\hosts
ipconfig /flushdns
```
然後回到一般的 cmd，再跑一次 watch.bat --once，這樣就會通了。



```bash
cd /d C:\Users\USER\Downloads
watch.bat --once
```
```bash
cd /workspace/wafercap
nohup python3 gpu_hold_all.py > hold.log 2>&1 &
sleep 8; cat hold.log; nvidia-smi
```
直接 kill 掉佔位程式：

```bash
kill $(cat ~/.gpu_hold.pid)
sleep 2; nvidia-smi
```
nvidia-smi 的顯存回到幾 MiB、下面的 Processes 顯示 No running processes，就代表 GPU 已經空出來了，可以直接跑你的東西。

如果 kill 之後顯存沒有釋放，就用強制關閉的方式：

```bash
pkill -9 -f gpu_hold_all.py
```
工作做完要再佔回去時：

```bash
cd /workspace/wafercap
nohup python3 gpu_hold_all.py > hold.log 2>&1 &
```
PS C:\Users\USER> ssh nina1031@nano4.nchc.org.tw
(nina1031@nano4.nchc.org.tw) Please select the 2FA login method.
1. Mobile APP OTP
2. Mobile APP PUSH
3. Email OTP
Login method: 1
(nina1031@nano4.nchc.org.tw) Password:
(nina1031@nano4.nchc.org.tw) OTP: 682936
Register this system with Red Hat Insights: rhc connect

Example:
# rhc connect --activation-key <key> --organization <org>

The rhc client and Red Hat Insights will enable analytics and additional
management capabilities on your system.
View your connected systems at https://console.redhat.com/insights

You can learn more about how to register your system
using rhc at https://red.ht/registration
Last login: Fri Oct  9 11:49:56 2026 from 140.110.109.164
[nina1031@25a-lgn02 ~]$ sacct -j 518883 --format=JobID,NodeList,Elapsed,State
JobID               NodeList    Elapsed      State
------------ --------------- ---------- ----------
518883           25a-hgpn007   00:21:07  COMPLETED
518883.batch     25a-hgpn007   00:21:07  COMPLETED
518883.exte+     25a-hgpn007   00:21:08  COMPLETED
[nina1031@25a-lgn02 ~]$ cd /work/nina1031/tiny
ls
run20-518847.out  run20-518860.out  run20.sh         tiny-518839.out  tiny.sh         train_tiny.py
run20-518858.out  run20-518883.out  tiny-518838.out  tiny_ckpt.pt     train_20min.py
timed out waiting for input: auto-logout
Connection to nano4.nchc.org.tw closed.
PS C:\Users\USER>
