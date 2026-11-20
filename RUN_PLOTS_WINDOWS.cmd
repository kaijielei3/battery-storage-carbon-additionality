@echo off
setlocal
cd /d "%~dp0"
python "04_Executable_Code\plot_from_archive.py" --root "%CD%" --out "%CD%\08_Audit\Plots_Recreated"
pause
