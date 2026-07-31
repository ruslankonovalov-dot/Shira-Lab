<#
.SYNOPSIS
    Shira Lab Launcher — PowerShell версия для скрытого запуска
.DESCRIPTION
    Запускает приложение через pythonw.exe без консольного окна.
    Можно закрепить на таскбаре как обычную программу.
#>

# Путь к корню проекта (где лежит этот скрипт)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Путь к pythonw.exe в venv
$PythonW = Join-Path $ScriptDir "venv\Scripts\pythonw.exe"
$RunPy   = Join-Path $ScriptDir "run.py"

# Проверки
if (-not (Test-Path $PythonW)) {
    Write-Error "Не найден pythonw.exe: $PythonW"
    exit 1
}
if (-not (Test-Path $RunPy)) {
    Write-Error "Не найден run.py: $RunPy"
    exit 1
}

# Переменные окружения
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = $ScriptDir

# Скрытый запуск через Start-Process (WindowStyle Hidden)
Start-Process -FilePath $PythonW -ArgumentList "`"$RunPy`"" -WindowStyle Hidden -WorkingDirectory $ScriptDir