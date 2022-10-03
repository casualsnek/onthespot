#!/bin/bash
rm -rf ./dist
rm -rf ./build
python3 -m venv venv
source ./venv/bin/activate
pip install pyinstaller
pip install -r requirements.txt
pyinstaller build.spec
chmod +x ./dist/onthespot