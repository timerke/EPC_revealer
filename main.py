"""
File to start application.
"""

import logging
import sys
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from main_window import MainWindow

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s.%(funcName)s: %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)
logger = logging.getLogger("revealer")
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)


def exception_hook(exc_type: Exception, exc_value: Exception, exc_traceback: "traceback"):
    """
    Function handles unexpected errors.
    :param exc_type: exception class;
    :param exc_value: exception instance;
    :param exc_traceback: traceback object.
    """

    traceback.print_exception(exc_type, exc_value, exc_traceback)
    traceback_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    show_exception("Error", str(exc_value), traceback_text)
    sys.exit(1)


def show_exception(msg_title: str, msg_text: str, exc: str = ""):
    """
    Function shows message box with error.
    :param msg_title: title of message box;
    :param msg_text: message text;
    :param exc: text of exception.
    """

    max_message_length = 500
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(msg_title)
    msg.setText(msg_text)
    if exc:
        msg.setInformativeText(str(exc)[-max_message_length:])
    msg.exec_()


sys.excepthook = exception_hook


if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
