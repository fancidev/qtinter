"""Launcher for multiple stopwatches"""

import qtinter
from PyQt6 import QtWidgets
import stopwatch1
import stopwatch2
import stopwatch3


class LauncherWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.button1 = QtWidgets.QPushButton(self)
        self.button1.setText("Launch Stopwatch 1")
        self.button1.clicked.connect(self.launch_stopwatch_1)

        self.button2 = QtWidgets.QPushButton(self)
        self.button2.setText("Launch Stopwatch 2")
        self.button2.clicked.connect(self.launch_stopwatch_2)

        self.button3 = QtWidgets.QPushButton(self)
        self.button3.setText("Launch Stopwatch 3")
        self.button3.clicked.connect(self.launch_stopwatch_3)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.button1)
        self.layout.addWidget(self.button2)
        self.layout.addWidget(self.button3)

        self.widgets = []

    def launch_stopwatch_1(self):
        widget = stopwatch1.MyWidget()
        widget.resize(250, 150)
        widget.show()
        self.widgets.append(widget)

    def launch_stopwatch_2(self):
        widget = stopwatch2.MyWidget()
        widget.resize(250, 150)
        widget.show()
        self.widgets.append(widget)

    def launch_stopwatch_3(self):
        widget = stopwatch3.MyWidget()
        widget.resize(250, 150)
        widget.show()
        self.widgets.append(widget)

    def closeEvent(self, event):
        QtWidgets.QApplication.quit()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    launcher = LauncherWidget()
    # launcher.resize(300, 200)
    launcher.show()

    with qtinter.using_asyncio_from_qt():
        app.exec()
