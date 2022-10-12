import os
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog
from runtimedata import get_logger

logger = get_logger('gui.minidialog')


class MiniDialog(QDialog):
    def __init__(self, parent=None):
        super(MiniDialog, self).__init__(parent)
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(self.path, 'qtui', 'notice.ui'), self)
        self.btn_close.clicked.connect(self.hide)
        logger.debug('Dialog item is ready..')

    def run(self, content, btn_hidden=False):
        if btn_hidden:
            self.btn_close.hide()
        else:
            self.btn_close.show()
        self.show()
        logger.debug(f"Displaying dialog with text '{content}'")
        self.lb_main.setText(str(content))
