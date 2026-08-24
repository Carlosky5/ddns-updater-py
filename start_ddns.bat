@echo off
cd /d "%~dp0"
python ddns.py --live %*
if errorlevel 1 pause