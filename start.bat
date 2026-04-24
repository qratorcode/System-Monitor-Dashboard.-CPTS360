@echo off
echo Starting SYSMON...

start wsl -e bash -c "cd /mnt/c/Users/anciu/OneDrive/Desktop/sysmon && node server.js"
timeout /t 2 /nobreak >nul

start wsl -e bash -c "cd /mnt/c/Users/anciu/OneDrive/Desktop/sysmon && python3 system_monitor_daemon.py"
timeout /t 2 /nobreak >nul

start "" "http://127.0.0.1:5500/index.html"

echo SYSMON is running. Close this window to stop.
pause