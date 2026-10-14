@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set "RUNAI_URL=https://runai.tpe1.local"
set "RUNAI_USER=caijingnina@gmail.com"
set "RUNAI_PASS=Nin@871031"
set "DISCORD_WEBHOOK=https://discordapp.com/api/webhooks/1557589487767519266/8aTkRjLRGKnfbjodrFvy16amXWbxe_P7AOgZH6a9hoJk6MGWIgmmqLpqz26K-h2ro9GR"
cd /d "%~dp0"
py runai_watch.py --insecure --log "%~dp0runai_history.csv" %*
if "%~1"=="" pause
