"""Report current geolocation"""

import asyncio
import os
import qtinter
import sys
from PyQt6 import QtCore, QtPositioning


async def get_location() -> str:
    """Return the current location as a string."""

    # A QGeoPositionInfoSource object needs a parent to control its lifetime.
    app = QtCore.QCoreApplication.instance()
    source = QtPositioning.QGeoPositionInfoSource.createDefaultSource(app)
    if source is None:
        raise RuntimeError("No QGeoPositionInfoSource is available")

    # This is a pattern to call a Qt method *after* installing signal handlers.
    asyncio.get_running_loop().call_soon(source.requestUpdate, 0)

    # Install two signal handlers to handle both success and failure.
    pos_task = asyncio.create_task(qtinter.asyncsignal(source.positionUpdated))
    err_task = asyncio.create_task(qtinter.asyncsignal(source.errorOccurred))

    # Wait for the first signal to occur.
    done, pending = await asyncio.wait([pos_task, err_task],
                                       return_when=asyncio.FIRST_COMPLETED)
    pos_task.cancel()
    err_task.cancel()
    await asyncio.gather(pos_task, err_task, return_exceptions=True)

    if pos_task in done:
        position: QtPositioning.QGeoPositionInfo = pos_task.result()
        return position.coordinate().toString()

    if err_task in done:
        error: QtPositioning.QGeoPositionInfoSource.Error = err_task.result()
        raise RuntimeError(f"Cannot obtain geolocation: {error}")


def main():
    if sys.platform == 'darwin':
        # QtPositioning requires QEventDispatcherCoreFoundation on macOS.
        # Set QT_EVENT_DISPATCHER_CORE_FOUNDATION or use QtGui.QGuiApplication.
        os.environ['QT_EVENT_DISPATCHER_CORE_FOUNDATION'] = '1'
    app = QtCore.QCoreApplication([])
    with qtinter.using_qt_from_asyncio():
        print(asyncio.run(get_location()))


if __name__ == "__main__":
    main()
