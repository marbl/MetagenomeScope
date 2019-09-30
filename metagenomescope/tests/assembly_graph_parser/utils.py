import os
import tempfile
import pytest
from _pytest.outcomes import Failed
from metagenomescope.assembly_graph_parser import parse


def run_tempfile_test(
    suffix, file_contents, err_expected, in_err, join_char="\n"
):
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
        the corresponding error message. (If err_expected is None, then this
        argument won't be used for anything; feel free to set it to None or ""
        or whatever.)

    join_char: str
        The character (or string, I guess; doesn't really matter) to use when
        joining file_contents. Defaults to \n, but you can do things like set
        this to "" if your lines in file_contents already have newlines
        included (as is the case with the output of .readlines()).

    Returns
    -------
    The output of parse() (but only if parsing "succeeds").

    References
    ----------
    CODELINK: Our use of temporary files in this function (using mkstemp(), and
    wrapping the close and unlink calls in a finally clause) is based on
    NetworkX's test code. See
    https://github.com/networkx/networkx/blob/master/networkx/readwrite/tests/test_gml.py.
    """
    filehandle, filename = tempfile.mkstemp(suffix=suffix)
    ei = None
    output_graph = None
    try:
        with open(filename, "w") as f:
            f.write(join_char.join(file_contents))
        if err_expected is not None:
            with pytest.raises(err_expected) as ei:
                parse(filename)
            assert in_err in str(ei.value)
        else:
            output_graph = parse(filename)
    except (Exception, Failed) as e:
        # To give more context about *why* a failure occurred, print error info
        # (then reraise the exception).
        # (And for reference, when the "with pytest.raises(...)" block fails
        # due to the expected error *not* being raised, that raises a pytest
        # "Failed" exception -- which we catch explicitly here, since it's
        # ultimately derived from BaseException instead of from Exception.)
        print("*** HEY, run_tempfile_test() FAILED. PRINTING EXCEPTION: ***")
        print(e)
        print(
            "EXCEPTION PRINTED. IF NOTHING SHOWED UP ABOVE, IT'S LIKELY THE "
            "assert STATEMENT RE: THE EXPECTED ERROR MESSAGE FAILED."
        )
        # NOTE: Using ei.value here apparently causes an error when pytest
        # throws Failed??? I'm keeping this uncommented because it's really
        # useful for testing other errors (i.e. the assert inside the try block
        # failed)
        if ei is not None:
            print("ANOTHER THING: 'ei' IS DEFINED. HERE'S str(ei.value):")
            print(str(ei.value))
            print("AND HERE IS type(ei.value):")
            print(type(ei.value))
        raise
    finally:
        os.close(filehandle)
        os.unlink(filename)
    return output_graph
