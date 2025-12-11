@echo off
chcp 65001

echo ===============================================
echo    Сборка TaskPlanner (PyInstaller)
echo ===============================================

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del TaskPlanner.spec 2>nul

py -m pip install --upgrade pip
py -m pip install pyinstaller tkcalendar

py -m PyInstaller --onefile --windowed --name=TaskPlanner --clean main.py

if exist "%~dp0dist\TaskPlanner.exe" (
    echo УСПЕХ! EXE создан: %~dp0dist\TaskPlanner.exe
    explorer "%~dp0dist"
) else (
    echo ОШИБКА! EXE не создан.
)

pause
