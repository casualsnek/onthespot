@echo off
echo ========= OnTheSpot Windows Build Script ===========
echo =^> Cleaning up !"
rmdir build /s /q
rmdir __pycache__ /s /q
rmdir venvwin /s /q
if exist dist\onthespot_win.exe (
    del /F /Q /A dist\onthespot_win.exe
)
echo =^> Creating virtual env.
python.exe -m venv venvwin
echo =^> Switching to virtual env.
echo =^> Now run phase 2 script 'build_winC2.bat'
venvwin\Scripts\activate.bat