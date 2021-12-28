"""
File with class and functions to reveal available devices.
"""

import asyncio
import logging
import select
import socket
from datetime import datetime, timedelta
from typing import Callable, Optional
import aiohttp
import psutil
from PyQt5.QtCore import pyqtSignal, QObject, QTimer

logger = logging.getLogger("revealer")
PORT = 8080


def analyze_page(html: str) -> Optional[str]:
    """
    Function parses text and determines which device the page belongs to.
    :return: name of device.
    """

    html = html.lower()
    if "аса" in html:
        return Devices.ASA
    if "eyepoint h10" in html:
        return Devices.EYE_POINT_H10
    if "eyepoint s2" in html:
        return Devices.EYE_POINT_S2
    if "standamellon" in html:
        return Devices.STANDAMELLON
    if "бвву" in html:
        return Devices.UIOB
    return None


def check_stop(func: Callable):
    """
    Decorator to check that search should not be stopped.
    :param func: decorated function.
    """

    def wrapper(self, *args):
        if self.stop_search:
            logger.info("Searching of devices has been stopped, revealer number %s", self.number)
            self.search_stopped.emit(self.number)
            return
        return func(self, *args)

    return wrapper


async def read_page(url: str) -> str:
    """
    Function gets page for given URL.
    :param url: URL of page.
    :return: text in page.
    """

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            return html


class Devices:
    """
    Class with devices.
    """

    ASA = "АСА"
    EYE_POINT_H10 = "EyePoint H10"
    EYE_POINT_S2 = "EyePoint S2"
    STANDAMELLON = "STANDAMELLON"
    UIOB = "БВВУ"


class Revealer(QObject):
    """
    Class for revealer.
    """

    TIME_DELAY: int = 100
    device_found = pyqtSignal(int, str)
    device_identified = pyqtSignal(str, str)
    search_completed = pyqtSignal(int)
    search_started = pyqtSignal(int)
    search_stopped = pyqtSignal(int)

    def __init__(self, number: int):
        """
        :param number: revealer number.
        """

        super().__init__()
        self._ip_addresses: list = []
        self._timer: QTimer = QTimer()
        self.number: int = number
        self.stop_search: bool = False

    @check_stop
    def _identify_sources(self):
        """
        Method identifies devices that have given IP addresses.
        """

        loop = asyncio.new_event_loop()
        for ip_address in self._ip_addresses:
            try:
                coroutine = asyncio.wait_for(read_page(f"http://{ip_address}:{PORT}"), timeout=1)
                html = loop.run_until_complete(coroutine)
            except asyncio.TimeoutError:
                coroutine.close()
                logger.error("Page at IP address '%s' was not read", ip_address)
            else:
                device = analyze_page(html)
                if device is not None:
                    self.device_identified.emit(ip_address, device)
        self.search_completed.emit(self.number)
        self._timer.singleShot(self.TIME_DELAY, self._start)

    @check_stop
    def _reveal(self, timeout: float = None):
        """
        Method detects available devices in local network.
        :param timeout: max waiting time for responses.
        :return: list of IP addresses.
        """

        waiting_time = 0.1
        if timeout is None:
            timeout = waiting_time
        timeout = timedelta(seconds=timeout)
        ifaces = psutil.net_if_addrs()
        for iface_name, iface in ifaces.items():
            if self.stop_search:
                return
            iface_name = iface_name.encode(errors="replace").decode(errors="replace")
            for address in iface:
                if self.stop_search:
                    return
                if address.family != socket.AF_INET:
                    continue
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        sock.bind((address.address, 0))
                        sock.sendto(("DISCOVER_CUBIELORD_REQUEST " + str(sock.getsockname()[1])).encode(),
                                    ("255.255.255.255", 8008))
                        sock.setblocking(0)
                        time_end = datetime.utcnow() + timeout
                        while True:
                            if self.stop_search:
                                return
                            time_now = datetime.utcnow()
                            time_left = (time_end - time_now).total_seconds()
                            if time_left < 0:
                                break
                            ready = select.select([sock], [], [], time_left)
                            if ready[0]:
                                data, address = sock.recvfrom(4096)
                                ip_address = str(address[0])
                                if data.startswith("DISCOVER_CUBIELORD_RESPONSE ".encode()):
                                    self.device_found.emit(self.number, ip_address)
                                    self._ip_addresses.append(ip_address)
                except Exception as exc:
                    logger.error("Failed to bind to interface %s, address %s: %s", iface_name, address.address, exc)
        self._timer.singleShot(self.TIME_DELAY, self._identify_sources)

    def _start(self):
        logger.info("A new cycle of searching for devices has been launched, revealer number %s", self.number)
        self.search_started.emit(self.number)
        self._ip_addresses = []
        self._timer.singleShot(self.TIME_DELAY, self._reveal)

    def start(self, number: int):
        """
        Method starts searching available devices in network.
        :param number: number for revealer.
        """

        self.number = number
        self.stop_search = False
        logger.info("Signal was received to start search for revealer number %s", self.number)
        self._start()

    def stop(self):
        """
        Method stops searching.
        """

        self.stop_search = True
        logger.info("Signal was received to stop search for revealer number %s", self.number)
