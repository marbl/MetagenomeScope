import os
import errno
from . import config
from .msg_utils import operation_msg


def check_file_existence(filepath, overwrite):
    """Returns True if the given filepath does exist as a non-directory file
       and overwrite is set to True.

       Returns False if the given filepath does not exist at all.

       Raises errors if:
        -The given filepath does exist but overwrite is False
        -The given filepath exists as a directory

       Note that this has some race conditions associated with it -- the
       user or some other party could circumvent these error-checks by either
       creating a file or creating a directory at the filepath after this check
       but before MetagenomeScope attempts to create a file there.

       We get around this by using os.fdopen() wrapped to os.open() with
       certain flags (based on whether or not the user passed -w) set,
       for the one place in this script where we directly write to a file
       (in save_aux_file()). This allows us to guarantee an error will be
       thrown and no data will be erroneously written in the first two cases,
       while (for most non-race-condition cases) allowing us to display a
       detailed error message to the user here, before we even try to open the
       file.
    """
    if os.path.exists(filepath):
        if os.path.isdir(filepath):
            raise IOError(filepath + config.IS_DIR_ERR)
        if not overwrite:
            raise IOError(filepath + config.EXISTS_ERR)
        return True
    return False


def safe_file_remove(filepath):
    """Safely (preventing race conditions of the file already being removed)
       removes a file located at the given file path.

       CODELINK: this function is based on User "Matt"'s answer to this Stack
       Overflow question: https://stackoverflow.com/questions/10840533/
       Link to Matt's SO profile: https://stackoverflow.com/users/810671/matt
    """
    try:
        os.remove(filepath)
    except OSError as error:
        # If the error matches errno.ENOENT ("No such file or directory"),
        # then something removed the file before we could. That's alright, and
        # we don't need to throw an exception.
        if error.errno != errno.ENOENT:
            # However, if the error doesn't match errno.ENOENT, then we know
            # that something strange happened -- maybe someone changed the file
            # to a directory before we tried to remove it, or something
            # similarly odd. We don't attempt to handle this case, and instead
            # we just raise the original error to inform the user.
            raise


def save_aux_file(
    aux_filename, source, dir_fn, layout_msg_printed, overwrite, warnings=True
):
    """Given a filename and a source of "input" for the file, writes to that
       file (using check_file_existence() accordingly).

       If aux_filename ends with ".xdot", we assume that source is a
       pygraphviz.AGraph object of which we will write its "drawn" xdot output
       to the file.

       Otherwise, we assume that source is just a string of text to write
       to the file.

       For info on how we use os.open() (and the effects of that), see this
       page on the MetagenomeScope wiki:
       https://github.com/marbl/MetagenomeScope/wiki/Note-on-File-Race-Conditions

       CODELINK: The use of os.open() in conjunction with the os.O_EXCL
       flag in order to prevent the race condition, as well as the background
       information for the linked wiki writeup on this solution, is based on
       Adam Dinwoodie (username "me_and")'s answer to this Stack
       Overflow question: https://stackoverflow.com/questions/10978869
       Link to Adam's SO profile: https://stackoverflow.com/users/220155/me-and

       If check_file_existence() gives us an error (or if os.open() gives
       us an error due to the flags we've used), we don't save the
       aux file in particular. The default behavior (if warnings=True) in this
       case is to print an error message accordingly [1]. However, if
       warnings=False and we get an error from either possible "error source"
       (check_file_existence() or os.open()) then this will
       throw an error. Setting warnings=False should only be done for
       operations that are required to generate a .db file -- care should be
       taken to ensure that .db files aren't partially created before trying
       save_aux_file with warnings=False, since that could result in an
       incomplete .db file being generated (which might confuse users).
       If warnings=False, then the value of layout_msg_printed is not used.

       [1] The error message's formatting depends partly on whether or not
       a layout message for the current component was printed (given here as
       layout_msg_printed, a boolean variable) -- if so (i.e.
       layout_msg_printed is True), the error message here is printed on a
       explicit newline and followed by a trailing newline. Otherwise, the
       error message here is just printed with a trailing newline.

       Returns True if the file was written successfully; else, returns False.
    """
    fullfn = os.path.join(dir_fn, aux_filename)

    if overwrite:
        flags = os.O_CREAT | os.O_TRUNC | os.O_WRONLY
    else:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

    try:
        check_file_existence(fullfn, overwrite)
        # We use the defined flags (based on whether or not -w was passed)
        # to ensure some degree of atomicity in our file operations here,
        # preventing errors whenever possible
        with os.fdopen(os.open(fullfn, flags, config.AUXMOD), "w") as file_obj:
            if aux_filename.endswith(".xdot"):
                file_obj.write(source.draw(format="xdot"))
            else:
                file_obj.write(source)
        return True
    except (IOError, OSError) as e:
        # An IOError indicates check_file_existence failed, and (far less
        # likely, but still technically possible) an OSError indicates
        # os.open failed
        msg = config.SAVE_AUX_FAIL_MSG + "%s: %s" % (aux_filename, e)
        if not warnings:
            raise type(e)(msg)
        # If we're here, then warnings == True.
        # Don't save this file, but continue the script's execution.
        if layout_msg_printed:
            operation_msg("\n" + msg, newline=True)
        else:
            operation_msg(msg, newline=True)
        return False
