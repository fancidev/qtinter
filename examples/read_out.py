"""Read out input using QTextToSpeech"""

import asyncio
import getopt
import qtinter
import sys
from PyQt6 import QtGui, QtTextToSpeech


async def read_out(engine: QtTextToSpeech.QTextToSpeech, echo=False):
    while True:
        try:
            line = await asyncio.get_running_loop().run_in_executor(None, input)
        except EOFError:
            break
        if echo:
            print(line)
        engine.say(line)
        if engine.state() == QtTextToSpeech.QTextToSpeech.State.Speaking:
            # If the line contains no speakable content, state remains Ready.
            state = await qtinter.asyncsignal(engine.stateChanged)
            assert state == QtTextToSpeech.QTextToSpeech.State.Ready


def main():
    app = QtGui.QGuiApplication([])

    engine = QtTextToSpeech.QTextToSpeech()
    locales = dict((l.name(), l) for l in engine.availableLocales())
    voices = dict((v.name(), v) for v in engine.availableVoices())
    usage = (f"usage: {sys.argv[0]} [options]\n"
             f"Read out text from stdin.\n"
             f"Options:\n"
             f"    -e          Echo each line before reading it out\n"
             f"    -h          Show this screen and exit\n"
             f"    -l locale   One of {', '.join(sorted(locales))} "
             f"(default: {engine.locale().name()})\n"
             f"    -p pitch    Number between -1.0 and +1.0 (default: 0.0)\n"
             f"    -r rate     Number between -1.0 and +1.0 (default: 0.0)\n"
             f"    -v voice    One of {', '.join(sorted(voices))} "
             f"(default: {engine.voice().name()})\n")

    try:
        args, rest = getopt.getopt(sys.argv[1:], "ehl:p:r:v:")
    except getopt.error:
        print(usage, file=sys.stderr)
        return 1

    if rest:
        print(usage, file=sys.stderr)
        return 1

    echo = False
    for opt, val in args:
        if opt == "-e":
            echo = True
        elif opt == "-h":
            print(usage)
            return 0
        elif opt == "-l":
            engine.setLocale(locales[val])
        elif opt == "-p":
            engine.setPitch(float(val))
        elif opt == "-r":
            engine.setRate(float(val))
        elif opt == "-v":
            engine.setVoice(voices[val])
        else:
            print(usage, file=sys.stderr)
            return 1

    with qtinter.using_qt_from_asyncio():
        asyncio.run(read_out(engine, echo))


if __name__ == "__main__":
    sys.exit(main())
