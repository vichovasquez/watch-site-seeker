@echo off
echo Starting Multi-Website Search and Match Web Application...
cd /d "%~dp0"
start http://localhost:8000
python main.py
pause
