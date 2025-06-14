@echo off
echo  =^> Installing 'pyinstaller' via pip...
pip install --upgrade pip
pip install wheel
pip install pyinstaller
echo  =^> Installing dependencies pip...
pip install winsdk
pip install -r requirements.txt
if exist ffbin_win\ffmpeg.exe (
    echo =^> Found 'ffbin_win' directory and ffmpeg binary.. Using ffmpeg binary append mode
    pyinstaller --onefile --noconsole --noconfirm --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" --add-data="src/onthespot/resources/*.png;onthespot/resources" --add-binary="ffbin_win/*.exe;onthespot/bin/ffmpeg" --paths="src/onthespot" --name="onthespot_win_ffm" --icon="src/onthespot/resources/icon.png" src\portable.py
) else (
    echo  =^> Building to use ffmpeg binary from system...
    pyinstaller --onefile --noconsole --noconfirm --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" --add-data="src/onthespot/resources/*.png;onthespot/resources" --paths="src/onthespot" --name="onthespot_win" --icon="src/onthespot/resources/icon.png" src\portable.py
)
echo  =^> Cleaning..
if exist onthespot_win.spec (
    del /F /Q /A onthespot_win.spec
)
if exist onthespot_win_ffm.spec (
    del /F /Q /A onthespot_win_ffm.spec
)
if exist build\ (
    rmdir build /s /q
)

if exist __pycache__\ (
    rmdir __pycache__ /s /q
)
if exist venvwin\ (
    rmdir venvwin /s /q
)

echo  =^> Done
