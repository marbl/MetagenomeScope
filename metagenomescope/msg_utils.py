import sys
from .config import DONE_MSG


def operation_msg(message, newline=False):
    """Prints a message (by default, no trailing newline), then flushes
    sys.stdout.

    Flushing sys.stdout helps to ensure that the user sees the message (even
    if it is followed by a long operation in this program). The trailing
    newline is intended for use with conclude_msg(), defined below.
    """
    if newline:
        print(message)
    else:
        print(message, end=" ")
    sys.stdout.flush()


def conclude_msg(message=DONE_MSG):
    """Prints a message indicating that a long operation was just finished.

    This message will usually be appended on to the end of the previous
    printed text (due to use of operation_msg), to save vertical terminal
    space (and look a bit fancy).
    """
    print(message)
