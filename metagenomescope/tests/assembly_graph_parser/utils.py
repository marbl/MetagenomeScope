import os
import tempfile
import pytest
from metagenomescope.assembly_graph_parser import parse


def run_tempfile_test(suffix, file_contents, err_expected, in_err):
    """Simple function that creates a tempfile and runs parse() on it.

    Parameters
    ----------
    suffix: str
        The suffix to assign to the tempfile's filename.

    file_contents: list
        All of the lines in the tempfile, represented as a list of strings.
        This'll be written to the tempfile before parse is called on the
        tempfile.

        If you'd like an example of what this looks like, see reset_glines()
        in test_validate_lastgraph.py.

    err_expected: None or Exception
        If None, this'll just call parse on the tempfile (with success
        implicitly expected).

        If this is not None, this'll expect that parse throws an error
        *of this type* while processing the tempfile (e.g. a ValueError).

    in_err: str
        If err_expected is not None, we assert that this text is contained in
        the corresponding error message.

    References
    ----------
    CODELINK: Our use of temporary files in this function (using mkstemp(), and
    wrapping the close and unlink calls in a finally clause) is based on
    NetworkX's test code. See
    https://github.com/networkx/networkx/blob/master/networkx/readwrite/tests/test_gml.py.
    """
    filehandle, filename = tempfile.mkstemp(suffix=suffix)
    try:
        with open(filename, "w") as f:
            f.write("\n".join(file_contents))
        if err_expected is not None:
            with pytest.raises(err_expected) as ei:
                parse(filename)
            assert in_err in str(ei.value)
        else:
            parse(filename)
    except Exception as e:
        # For some reason, I don't seem to be getting detailed error messages
        # when the stuff in this function fails. So this just prints the error
        # message to stdout then re-raises the exception.
        # (And for reference, when the "with pytest.raises(...)" block fails
        # due to the expected error *not* being raised, that raises a pytest
        # "Failed" exception -- which is a subclass of Exception, so that'll be
        # caught by this except block. Phew!)
        print("*** HEY, run_tempfile_test() FAILED. PRINTING EXCEPTION: ***")
        print("NOTE THAT THE EXCEPTION MIGHT SHOW UP ABOVE FOR SOME REASON;")
        print("IDK WHY. IN MY DEFENSE, COMPUTERS ARE HARD")
        print(e)
        raise
    finally:
        os.close(filehandle)
        os.unlink(filename)
