@echo off
setlocal
cd /d "%~dp0"
python "04_Executable_Code\V84_seven_product_ED.py" --source "05_Source_Inputs\V77_RTS_SELECTED_UPLOAD.zip" --reserves "05_Source_Inputs\V82_RTS_RESERVES_UPLOAD.zip" --out "RECOMPUTED_seasonal" --starts 0,2184,4392,6576 --hours 168 --prices 0,25,75,200 --timeout 90
pause
