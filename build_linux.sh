#!/bin/bash
echo "========= OnTheSpot Linux Build Script ==========="
echo " => Cleaning up !"
rm -rf __pycache__
if [ -f "./dist/onthespot_linux" ]; then
    rm ./dist/onthespot_linux
fi
rm -rf ./build
rm -rf ./venv
echo " => Creating virtual env."
python3 -m venv venv
echo " => Switching to virtual env."
source ./venv/bin/activate
echo " => Installing 'pyinstaller' via pip..."
pip install pyinstaller
echo " => Installing dependencies pip..."
pip install -r requirements.txt
if [ -f "ffbin_nix/ffmpeg" ]; then
    echo " => Found 'ffbin_win' directory and ffmpeg binary.. Using ffmpeg binary append mode "
    pyinstaller --onefile \
                --add-data="gui/qtui/*.ui:qui/qtui" \
                --add-data="resources/*.png:resources" \
                --add-binary="ffbin_nix/*:bin/ffmpeg" \
                --paths="." \
                --name="onthespot_linux_ffm" \
                --icon="resources/icon.png" \
                __init__.py
else
    echo " => Building to use ffmpeg binary from system... "
    pyinstaller --onefile \
                --add-data="gui/qtui/*.ui:gui/qtui" \
                --add-data="resources/*.png:resources" \
                --paths="." \
                --name="onthespot_linux" \
                --icon="resources/icon.png" \
                __init__.py
fi
echo " => Setting permissions.. "
chmod +x ./dist/onthespot_linux
echo " => Cleaning.. "
rm onthespot_linux.spec
rm -rf ./build
rm -rf __pycache__
echo " => Done "
