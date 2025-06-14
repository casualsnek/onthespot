#!/bin/bash

clean_build_dirs () {
    [ -d ./__pycache__ ] && rm -rf __pycache__
    [ -d ./build ] && rm -rf ./build
    [ -d ./venv ] && rm -rf ./venv
    [ -f ./onthespot_linux.spec ] && rm ./onthespot_linux.spec
    [ -f ./onthespot_linux_ffm.spec ] && rm ./onthespot_linux_ffm.spec
}


echo "========= OnTheSpot Linux Build Script ==========="
echo " => Cleaning up !"
[ -f ./dist/onthespot_linux ] && rm ./dist/onthespot_linux
[ -f ./dist/onthespot_linux_ffm ] && rm ./dist/onthespot_linux_ffm
clean_build_dirs

echo " => Creating virtual env."
python3 -m venv venv

echo " => Switching to virtual env."
source ./venv/bin/activate

echo " => Installing 'pyinstaller' via pip..."
pip install pyinstaller

echo " => Installing dependencies to venv with pip..."
pip install -r requirements.txt

if [ -f "ffbin_nix/ffmpeg" ]; then
    echo " => Found 'ffbin_win' directory and ffmpeg binary.. Using ffmpeg binary append mode "
    pyinstaller --onefile \
                --add-data="src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
                --add-data="src/onthespot/resources/*.png:onthespot/resources" \
                --add-data="src/onthespot/resources/*.qss:onthespot/resources" \
                --add-binary="ffbin_nix/*:onthespot/bin/ffmpeg" \
                --paths="src/onthespot" \
                --name="onthespot_linux_ffm" \
                --icon="src/onthespot/resources/icon.png" \
                src/portable.py
else
    echo " => Building to use ffmpeg binary from system... "
    pyinstaller --onefile \
                --add-data="src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
                --add-data="src/onthespot/resources/*.png:onthespot/resources" \
                --add-data="src/onthespot/resources/*.qss:onthespot/resources" \
                --paths="src/onthespot" \
                --name="onthespot_linux" \
                --icon="src/onthespot/resources/icon.png" \
                src/portable.py
fi
echo " => Setting executable permissions.. "
[ -f ./dist/onthespot_linux ] && chmod +x ./dist/onthespot_linux &>./build_nix.log
[ -f ./dist/onthespot_linux_ffm ] && chmod +x ./dist/onthespot_linux_ffm &>./build_nix.log

echo " => Cleaning .. "
clean_build_dirs

echo " => Done "
