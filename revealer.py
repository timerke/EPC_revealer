"""
File with class and functions to reveal available devices.
"""

import asyncio
import select
import socket
from datetime import datetime, timedelta
from typing import Optional
import aiohttp
import psutil
from PyQt5.QtCore import pyqtSignal, QObject


def analyze_page(html: str) -> Optional[str]:
    """
    Function parses text and determines which device the page belongs to.
    :return: name of device.
    """

    html = html.lower()
    if "бвву" in html:
        return Devices.UIOB
    if "eyepoint s2" in html:
        return Devices.EYE_POINT_S2
    if "аса" in html:
        return Devices.ASA
    if "standamellon" in html:
        return Devices.STANDAMELLON
    return None


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
    EYE_POINT_S2 = "EyePoint S2"
    STANDAMELLON = "STANDAMELLON"
    UIOB = "БВВУ"


class Revealer(QObject):
    """
    Class for revealer.
    """

    device_found = pyqtSignal(int, str)
    device_identified = pyqtSignal(str, str)
    search_started = pyqtSignal(int)
    search_completed = pyqtSignal(int)

    def __init__(self, number: int):
        """
        :param number: revealer number.
        """

        super().__init__()
        self._ip_addresses = []
        self._number = number
        self._stop = False

    def _identify_sources(self):
        """
        Method identifies devices that have given IP addresses.
        """

        loop = asyncio.new_event_loop()
        for ip_address in self._ip_addresses:
            url = f"http://{ip_address}"
            try:
                coroutine = asyncio.wait_for(read_page(url), timeout=1)
                html = loop.run_until_complete(coroutine)
            except asyncio.TimeoutError:
                coroutine.close()
                print(f"Page at address {url} was not read")
            else:
                device = analyze_page(html)
                if device is not None:
                    self.device_identified.emit(ip_address, device)

    def _reveal(self, timeout: float = None):
        """
        Method detects available devices in network.
        :param timeout: max waiting time for responses.
        :return: list of IP addresses.
        """

        waiting_time = 0.05
        if timeout is None:
            timeout = waiting_time
        timeout = timedelta(seconds=timeout)
        ifaces = psutil.net_if_addrs()
        for iface_name, iface in ifaces.items():
            if self._stop:
                return
            iface_name = iface_name.encode(errors="replace").decode(errors="replace")
            for address in iface:
                if self._stop:
                    return
                if address.family != socket.AF_INET:
                    continue
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        sock.bind((address.address, 0))
                        sock.sendto(
                            ("DISCOVER_CUBIELORD_REQUEST " + str(sock.getsockname()[1])).encode(),
                            ("255.255.255.255", 8008))
                        sock.setblocking(0)
                        t_end = datetime.utcnow() + timeout
                        while True:
                            if self._stop:
                                return
                            t_now = datetime.utcnow()
                            d_t = (t_end - t_now).total_seconds()
                            if d_t < 0:
                                break
                            ready = select.select([sock], [], [], d_t)
                            if ready[0]:
                                data, address = sock.recvfrom(4096)
                                ip_address = str(address[0])
                                if data.startswith("DISCOVER_CUBIELORD_RESPONSE ".encode()):
                                    self.device_found.emit(self._number, ip_address)
                                    self._ip_addresses.append(ip_address)
                except Exception:
                    print(f"Failed to bind to interface {iface_name}, address {address.address}")

    def start(self):
        """
        Method starts searching available devices in network.
        """

        while not self._stop:
            self.search_started.emit(self._number)
            self._ip_addresses = []
            self._reveal()
            self._identify_sources()
            self.search_completed.emit(self._number)

    def stop(self):
        """
        Method stops searching.
        """

        self._stop = True
