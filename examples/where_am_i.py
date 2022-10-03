"""Report current geolocation"""

import asyncio
import qtinter
from PyQt6 import QtGui, QtPositioning


async def get_location() -> str:
    """Return the current location as a string."""

    app = QtGui.QGuiApplication.instance()
    if not isinstance(app, QtGui.QGuiApplication):
        raise RuntimeError(
            "QtPositioning requires QGuiApplication or QApplication instance")

    # A QGeoPositionInfoSource object uses a parent to control its lifetime.
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
    app = QtGui.QGuiApplication([])
    with qtinter.using_qt_from_asyncio():
        print(asyncio.run(get_location()))


if __name__ == "__main__":
    main()
