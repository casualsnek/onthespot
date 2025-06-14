#!/usr/bin/env python3
import os
import sys
from .frontends import *

def main():
    selected_frontend = os.environ.get('ONTHESPOT_FRONTEND', 'qt_pyside')
    if selected_frontend in ['qt_pyside', 'qt', 'qt6']:
        pass
    else:
        print(f'The onthespot frontend "{selected_frontend}" is not supported." ')
        print('Supported frontends: qt_pyside, qt, qt6')
        sys.exit(1)


if __name__ == '__main__':
    main()
