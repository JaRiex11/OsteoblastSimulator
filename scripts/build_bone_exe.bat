@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo === Установка PyInstaller ===
python -m pip install -q pyinstaller

echo === Сборка BoneLatticeSimulator (onedir) ===
python -m PyInstaller --noconfirm --onedir --windowed ^
  --name BoneLatticeSimulator ^
  --paths "%CD%" ^
  --hidden-import openpnm ^
  --hidden-import networkx ^
  --hidden-import pyvista ^
  --hidden-import pyvistaqt ^
  --hidden-import vtkmodules ^
  --hidden-import pyqtgraph ^
  --hidden-import matplotlib.backends.backend_agg ^
  --collect-all pyvista ^
  --collect-submodules vtkmodules ^
  bone_run.py

if %ERRORLEVEL% EQU 0 (
  echo.
  echo Готово: dist\BoneLatticeSimulator\BoneLatticeSimulator.exe
  echo Запускайте exe из папки dist\BoneLatticeSimulator\
  echo Рядом с exe создаются output\ и bone_gui_settings.json
) else (
  echo Ошибка сборки.
)
pause
