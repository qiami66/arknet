@echo off
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYEXE=D:\DeepSeekDSH\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
"%PYEXE%" sync.py >> sync.log 2>&1
exit /b %ERRORLEVEL%
