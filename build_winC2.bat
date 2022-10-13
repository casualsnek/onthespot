@echo off
echo  =^> Installing 'pyinstaller' via pip...
pip install --upgrade pip
pip install wheel
pip install pyinstaller
echo  =^> Installing dependencies pip...
pip install winsdk
pip install simpleaudio
pip install -r requirements.txt
if exist ffbin_win\ffmpeg.exe (
    echo =^> Found 'ffbin_win' directory and ffmpeg binary.. Using ffmpeg binary append mode
    pyinstaller --onefile --noconfirm --hidden-import simpleaudio --add-binary="ffbin_win/*.exe;bin/ffmpeg" --add-data="gui/qtui/*.ui;gui/qtui" --paths="." --name="onthespot_win" __init__.py
) else (
    echo  =^> Building to use ffmpeg binary from system...
    pyinstaller --onefile --noconfirm --hidden-import simpleaudio --add-data="gui/qtui/*.ui;gui/qtui" --paths="." --name="onthespot_win" __init__.py
)
echo  =^> Cleaning..
del /F /Q /A onthespot_win.spec
rmdir build /s /q
rmdir __pycache__ /s /q
echo  =^> Done