from PyQt5 import QtNetwork
from PyQt5.QtCore import Qt, QObject, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QLabel


class LabelWithThumb(QWidget):
    def __init__(self, thumb_url, label_text, qt_nam, thumb_enabled=True, thumb_height=60, parent=None):
        super(LabelWithThumb, self).__init__(parent)
        self.__thumb_url = thumb_url
        self.__text_label = QLabel()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.__text_label.setText(label_text)
        self.__text_label.setWordWrap(True)
        self.__text_label.setToolTip(label_text)
        self.__text_label.setAlignment(Qt.AlignLeft)
        if thumb_enabled:
            self.__thumb_label = QLabel()
            self.__thumb_label.setFixedHeight(thumb_height)
            self.__thumb_label.setFixedWidth(thumb_height)
            self.__thumb_label.setToolTip(label_text)
            layout.addWidget(self.__thumb_label)
            self.loader = LabelURLSetImage(self.__thumb_label, QtNetwork.QNetworkRequest(QUrl(self.__thumb_url)),
                                           qt_nam)
        layout.addWidget(self.__text_label)
        self.setLayout(layout)


class LabelURLSetImage(QObject):
    def __init__(self, parent, req_url, net_mgr, thumb_height=60):
        self.__thumb_height = thumb_height
        self.fetch_task = net_mgr.get(req_url)
        self.fetch_task.finished.connect(self.resolve_fetch)
        super(LabelURLSetImage, self).__init__(parent)

    def resolve_fetch(self):
        response = self.fetch_task.readAll()
        pixmap = QPixmap()
        pixmap.loadFromData(response)
        pixmap = pixmap.scaled(self.__thumb_height, self.__thumb_height)
        self.parent().setPixmap(pixmap)