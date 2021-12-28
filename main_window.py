"""
File with class for main window.
"""

import os
import webbrowser
from typing import Optional
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread
from PyQt5.QtGui import QColor, QCloseEvent, QFont, QIcon
from PyQt5.QtWidgets import QListWidgetItem, QMainWindow
from revealer import Devices, PORT, Revealer


COLORS = {Devices.ASA: "red",
          Devices.EYE_POINT_H10: "orange",
          Devices.EYE_POINT_S2: "green",
          Devices.STANDAMELLON: "cyan",
          Devices.UIOB: "blue"}
DEFAULT_COLOR = "black"


def check_correct_revealer(func):
    """
    Decorator to check that data was sent from correct revealer.
    :param func: decorated method.
    """

    def wrapper(self, revealer_number: int, *args):
        """
        :param self:
        :param revealer_number: number of revealer that sent data;
        :param args: data from revealer.
        """

        if self.revealer_number != revealer_number:
            return
        return func(self, revealer_number, *args)

    return wrapper


class MainWindow(QMainWindow):
    """
    Class for main window.
    """

    search_started = pyqtSignal(int)
    search_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.revealer_number: int = 0
        self._new_ip_addresses: np.ndarray = np.array([])
        self._old_ip_addresses: np.ndarray = np.array([])
        self._thread: QThread = QThread(parent=self)
        self._thread.setTerminationEnabled(True)
        self._revealer: Revealer = Revealer(self.revealer_number)
        self._revealer.moveToThread(self._thread)
        self._revealer.search_completed.connect(self.handle_completion)
        self._revealer.search_started.connect(self.handle_start)
        self._revealer.search_stopped.connect(self.handle_stop)
        self._revealer.device_found.connect(self.add_device)
        self._revealer.device_identified.connect(self.identify_device)
        self.search_started.connect(self._revealer.start)
        self.search_stopped.connect(self._revealer.stop)
        self._thread.start()
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
        uic.loadUi(os.path.join(dir_name, "gui", "main_window.ui"), self)
        self.setWindowTitle("Revealer")
        self.setWindowIcon(QIcon(os.path.join(dir_name, "gui", "icon.png")))
        self.setMinimumSize(200, 200)
        self.setMaximumSize(400, 400)
        self.button_search.toggled.connect(self.start_or_stop_search)
        self.list_widget_available_devices.itemDoubleClicked.connect(self.open_link)

    @check_correct_revealer
    @pyqtSlot(int, str)
    def add_device(self, _: int, ip_address: str):
        """
        Slot adds new available device.
        :param _: number of revealer that sent signal;
        :param ip_address: IP address of device.
        """

        self._new_ip_addresses = np.append(self._new_ip_addresses, ip_address)
        if ip_address not in list(self._old_ip_addresses):
            self._add_item(ip_address)

    def closeEvent(self, close_event: QCloseEvent):
        """
        Method closes main window.
        :param close_event: close event.
        """

        if self._thread:
            self._revealer.stop()
            del self._revealer
            self._thread.quit()
        super().closeEvent(close_event)

    @check_correct_revealer
    @pyqtSlot(int)
    def handle_completion(self, _: int):
        """
        Slot handles signal that one search is complete.
        :param _: number of revealer that sent signal.
        """

        removed_addresses = np.setdiff1d(self._old_ip_addresses, self._new_ip_addresses)
        for address in removed_addresses:
            items = self.list_widget_available_devices.findItems(address, Qt.MatchExactly)
            items.extend(self.list_widget_available_devices.findItems(f"{address} (", Qt.MatchStartsWith))
            for item in items:
                row = self.list_widget_available_devices.row(item)
                self.list_widget_available_devices.takeItem(row)

    @check_correct_revealer
    @pyqtSlot(int)
    def handle_start(self, _: int):
        """
        Slot handles signal that search is started.
        :param _: number of revealer that sent signal.
        """

        self._old_ip_addresses = self._new_ip_addresses[:]
        self._new_ip_addresses = np.array([])
        if not self.button_search.isEnabled():
            self.button_search.setEnabled(True)

    @check_correct_revealer
    @pyqtSlot(int)
    def handle_stop(self, _: int):
        """
        Slot handles signal that search was stopped.
        :param _: number of revealer that sent signal.
        """

        if not self.button_search.isEnabled():
            self.button_search.setEnabled(True)

    @pyqtSlot(str, str)
    def identify_device(self, ip_address: str, device: str):
        """
        Slot handles signal with IP address and name of device.
        :param ip_address: IP address of device;
        :param device: name of device.
        """

        items = self.list_widget_available_devices.findItems(ip_address, Qt.MatchExactly)
        items.extend(self.list_widget_available_devices.findItems(f"{ip_address} (", Qt.MatchStartsWith))
        for item in items:
            if item.text() == f"{ip_address} ({device})":
                continue
            color = COLORS.get(device, DEFAULT_COLOR)
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
        webbrowser.open(f"http://{ip_address}:{PORT}")

    @pyqtSlot(bool)
    def start_or_stop_search(self, status: bool):
        """
        Slot starts and stops searching for available devices.
        :param status: if True then searching should be started.
        """

        if status:
            self._clear()
            self.revealer_number += 1
            self.search_stopped.emit()
            self.search_started.emit(self.revealer_number)
            button_label = "Стоп"
        else:
            self.search_stopped.emit()
            button_label = "Искать"
        self.button_search.setText(button_label)
        self.button_search.setEnabled(False)
