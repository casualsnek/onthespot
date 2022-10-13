import os
from PyQt5.QtWidgets import QHBoxLayout, QWidget
from runtimedata import downloaded_data, cancel_list, failed_downloads, downloads_status, download_queue
from showinfm import show_in_file_manager


class DownloadActionsButtons(QWidget):
    def __init__(self, dl_id, pbar, cancel_btn, remove_btn, locate_btn, parent=None):
        super(DownloadActionsButtons, self).__init__(parent)
        self.__id = dl_id
        self.cancel_btn = cancel_btn
        self.remove_btn = remove_btn
        self.locate_btn = locate_btn
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        cancel_btn.clicked.connect(self.cancel_item)
        remove_btn.clicked.connect(self.retry_item)
        locate_btn.clicked.connect(self.locate_file)
        layout.addWidget(pbar)
        layout.addWidget(cancel_btn)
        layout.addWidget(remove_btn)
        layout.addWidget(locate_btn)
        self.setLayout(layout)

    def locate_file(self):
        if self.__id in downloaded_data:
            if downloaded_data[self.__id].get('media_path', None):
                show_in_file_manager(os.path.abspath(downloaded_data[self.__id]['media_path']))

    def cancel_item(self):
        cancel_list[self.__id] = {}
        self.cancel_btn.hide()

    def retry_item(self):
        if self.__id in failed_downloads:
            downloads_status[self.__id]["status_label"].setText("Waiting")
            self.remove_btn.hide()
            download_queue.put(failed_downloads[self.__id])
            self.cancel_btn.show()
