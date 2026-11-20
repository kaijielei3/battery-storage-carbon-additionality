@echo off
setlocal
cd /d "%~dp0"
python "04_Executable_Code\V84_annual_restartable.py" --source "05_Source_Inputs\V77_RTS_SELECTED_UPLOAD.zip" --reserves "05_Source_Inputs\V82_RTS_RESERVES_UPLOAD.zip" --out "RECOMPUTED_annual" --prices 0,25 --max-windows 53 --timeout 120
pause
