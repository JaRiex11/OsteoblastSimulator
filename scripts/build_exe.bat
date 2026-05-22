@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo === Установка PyInstaller ===
python -m pip install -q pyinstaller

echo === Сборка OsteoblastSimulator.exe ===
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name OsteoblastSimulator ^
  --paths "%CD%" ^
  --hidden-import networkx ^
  --hidden-import matplotlib.backends.backend_tkagg ^
  --collect-all matplotlib ^
  run.py

if %ERRORLEVEL% EQU 0 (
  echo.
  echo Готово: dist\OsteoblastSimulator.exe
  echo Скопируйте .exe в любую папку; рядом создастся output\ для результатов.
) else (
  echo Ошибка сборки.
)
pause
