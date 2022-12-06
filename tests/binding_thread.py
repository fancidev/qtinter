import importlib
import sys
import threading

binding_name = sys.argv[1]
token = sys.argv[2]
QtCore = importlib.import_module(f"{binding_name}.QtCore")
app = QtCore.QCoreApplication([])


def f():
    print(token)


def run():
    qt_loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(0, f)
    QtCore.QTimer.singleShot(0, qt_loop.quit)
    if hasattr(qt_loop, "exec"):
        qt_loop.exec()
    else:
        qt_loop.exec_()


thread = threading.Thread(target=run)
thread.start()
thread.join()
