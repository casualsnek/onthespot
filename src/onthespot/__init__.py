#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication
from .gui.mainui import MainWindow
from .gui.minidialog import MiniDialog
from .runtimedata import get_logger


def main():
    logger = get_logger('__init__')
    logger.info('Starting application in \n3\n2\n1')
    app = QApplication(sys.argv)
    _dialog = MiniDialog()
    window = MainWindow(_dialog, sys.argv[1] if len(sys.argv) >= 2 else '' )
    app.setDesktopFileName('org.eu.casualsnek.onthespot')
    app.exec_()
    logger.info('Good bye ..')


if __name__ == '__main__':
    main()
