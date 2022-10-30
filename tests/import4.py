"""Helper script used by test_import.py"""

import coverage
coverage.process_startup()

import sys

if sys.platform == 'win32':
    import qtinter._unix_events
else:
    import qtinter._windows_events
