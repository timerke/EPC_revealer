"""
File with class for main window.
"""

import os
import webbrowser
from typing import Optional
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, Qt, QThread
from PyQt5.QtGui import QColor, QCloseEvent, QFont, QIcon
from PyQt5.QtWidgets import QListWidgetItem, QMainWindow
from revealer import Devices, Revealer


class MainWindow(QMainWindow):
    """
    Class for main window.
    """

    COLORS = {Devices.ASA: "blue",
              Devices.EYE_POINT_S2: "green",
              Devices.STANDAMELLON: "brown",
              Devices.UIOB: "orange"}

    def __init__(self):
        super().__init__()
        self._revealer = None
        self._revealer_number = 0
        self._thread = None
        self._new_ip_addresses = np.array([])
        self._old_ip_addresses = np.array([])
        self._init_ui()

    def _add_item(self, text: str, row: Optional[int] = None, color: Optional[str] = None):
        """
        Method adds item to list widget.
        :param text: text for item;
        :param row: row to insert item;
        :param color: color for item.
        """

        item = QListWidgetItem(text)
        item.setTextAlignment(Qt.AlignHCenter)
        font = QFont()
        font.setBold(True)
        font.setUnderline(True)
        item.setFont(font)
        if color is not None:
            item.setForeground(QColor(color))
        if row is None:
            self.list_widget_available_devices.addItem(item)
            self.list_widget_available_devices.sortItems()
        else:
            self.list_widget_available_devices.insertItem(row, item)

    def _clear(self):
        """
        Method clears all data.
        """

        self.list_widget_available_devices.clear()
        self._new_ip_addresses = np.array([])
        self._old_ip_addresses = np.array([])

    def _init_ui(self):
        """
        Method initializes widget on main window.
        """

        dir_name = os.path.dirname(os.path.abspath(__file__))
        ui_file_name = os.path.join(dir_name, "gui", "main_window.ui")
        uic.loadUi(ui_file_name, self)
        self.setWindowTitle("Revealer")
        icon_file_name = os.path.join(dir_name, "gui", "icon.png")
        self.setWindowIcon(QIcon(icon_file_name))
        self.button_search.clicked.connect(self.start_search)
        self.list_widget_available_devices.itemDoubleClicked.connect(self.open_link)

    @pyqtSlot(int, str)
    def add_device(self, revealer_number: int, ip_address: str):
        """
        Slot adds new available device.
        :param revealer_number: number of revealer that sent signal;
        :param ip_address: IP address of device.
        """

        if self._revealer_number != revealer_number:
            return
        self._new_ip_addresses = np.append(self._new_ip_addresses, ip_address)
        if ip_address not in list(self._old_ip_addresses):
            self._add_item(ip_address)

    def closeEvent(self, _: QCloseEvent):
        """
        Method closes main window.
        :param _: close event.
        """

        if self._thread:
            self._revealer.stop()
            del self._revealer
            self._thread.quit()
        super().closeEvent(_)

    @pyqtSlot(int)
    def handle_completion(self, revealer_number: int):
        """
        Slot handles signal that one search is complete.
        :param revealer_number: number of revealer that sent signal.
        """

        if self._revealer_number != revealer_number:
            return
        removed_addresses = np.setdiff1d(self._old_ip_addresses, self._new_ip_addresses)
        for address in removed_addresses:
            items = self.list_widget_available_devices.findItems(address, Qt.MatchStartsWith)
            for item in items:
                row = self.list_widget_available_devices.row(item)
                self.list_widget_available_devices.takeItem(row)

    @pyqtSlot(int)
    def handle_start(self, revealer_number: int):
        """
        Slot handles signal that search is started.
        :param revealer_number: number of revealer that sent signal.
        """

        if self._revealer_number != revealer_number:
            return
        self._old_ip_addresses = self._new_ip_addresses[:]
        self._new_ip_addresses = np.array([])

    @pyqtSlot(str, str)
    def identify_device(self, ip_address: str, device: str):
        """
        Slot handles signal with IP address and name of device.
        :param ip_address: IP address of device;
        :param device: name of device.
        """

        items = self.list_widget_available_devices.findItems(ip_address, Qt.MatchStartsWith)
        for item in items:
            color = self.COLORS.get(device)
            row = self.list_widget_available_devices.row(item)
            self.list_widget_available_devices.takeItem(row)
            self._add_item(f"{ip_address} ({device})", row, color)

    @staticmethod
    @pyqtSlot(QListWidgetItem)
    def open_link(item: QListWidgetItem):
        """
        Slot opens link.
        :param item: clicked item in list widget.
        """

        ip_address = item.text().split(" ")[0]
        webbrowser.open(f"http://{ip_address}")

    @pyqtSlot()
    def start_search(self):
        """
        Slot starts searching for available devices.
        """

        self._clear()
        if self._thread:
            self._revealer.stop()
            del self._revealer
            self._thread.quit()
        self._thread = QThread(parent=self)
        self._thread.setTerminationEnabled(True)
        self._revealer = Revealer(self._revealer_number)
        self._revealer.moveToThread(self._thread)
        self._revealer.search_started.connect(self.handle_start)
        self._revealer.search_completed.connect(self.handle_completion)
        self._revealer.device_found.connect(self.add_device)
        self._revealer.device_identified.connect(self.identify_device)
        self._thread.started.connect(self._revealer.start)
        self._thread.start()
