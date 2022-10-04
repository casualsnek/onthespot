rmdir build /s /q
rmdir dist /s /q
pip install winsdk
python.exe -m venv venv
venv\Scripts\activate.bat
pip install pyinstaller
pip install winsdk
pip install -r requirements.txt
pyinstaller build.spec
