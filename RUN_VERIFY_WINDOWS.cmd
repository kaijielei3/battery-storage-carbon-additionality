@echo off
setlocal
cd /d "%~dp0"
python "04_Executable_Code\verify_release.py" --root "%CD%" --out "%CD%\08_Audit\Verification_Rerun"
if errorlevel 1 (
  echo VERIFICATION FAILED. See 08_Audit\Verification_Rerun.
) else (
  echo VERIFICATION PASSED. See 08_Audit\Verification_Rerun.
)
pause
