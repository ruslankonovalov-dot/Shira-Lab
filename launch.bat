@echo off
REM Shira Lab Launcher — запуск без консольного окна
REM Использует pythonw.exe из venv для скрытого запуска

cd /d "%~dp0"

REM Путь к pythonw.exe в venv (без консоли)
set "PYTHONW=%~dp0venv\Scripts\pythonw.exe"

REM Устанавливаем кодировку UTF-8
set PYTHONUTF8=1
set PYTHONPATH=%~dp0

REM Запуск через pythonw.exe — консоль не появляется
start "" "%PYTHONW%" "%~dp0run.py"