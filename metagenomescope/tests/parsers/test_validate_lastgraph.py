import pytest
from io import StringIO
from metagenomescope.errors import GraphParsingError
from metagenomescope.parsers import validate_lastgraph_file


def get_validate_err(glines):
    # What this is doing: create a string consisting of all the lines in
    # glines, separated by newlines, then shove that into a StringIO.
    bad_lg = StringIO("\n".join(glines))
    # Assume that the LastGraph file represented by bad_lg will fail
    # validation, and return the accompanying error message.
    # (If a GraphParsingError *isn't* raised, this'll throw an error saying
    # DID NOT RAISE or something.)
    with pytest.raises(GraphParsingError) as ei:
        validate_lastgraph_file(bad_lg)
    return str(ei.value)


def run_validate(glines):
    # Like get_validate_err(), but this assumes that validation will work.
    good_lg = StringIO("\n".join(glines))
    validate_lastgraph_file(good_lg)


def reset_glines():
    return [
        "2\t10\t1\t1",
        "NODE\t1\t1\t5\t5\t0\t0",
        "G",
        "C",
        "NODE\t2\t6\t20\t5\t0\t0",
        "GGAAGG",
        "TTTTAC",
        "ARC\t1\t2\t5",
        "ARC\t2\t1\t9",
    ]


def test_validate_lastgraph_good():
    # Try out some known-to-be-correct examples
    with open("metagenomescope/tests/input/cycletest_LastGraph", "r") as ctlg:
        validate_lastgraph_file(ctlg)
    with open("metagenomescope/tests/input/longtest_LastGraph", "r") as ltlg:
        validate_lastgraph_file(ltlg)
    # Okay, now we'll try to break things.


def test_validate_lastgraph_node_interrupted():
    # Here, we test the error where a NODE block is interrupted by the
    # declaration of another NODE.
    # Remove the fourth line of the file (it's 0-indexed, hence 3).
    glines = reset_glines()
    glines.pop(3)
    assert "Line 4: Node block ends too early." in get_validate_err(glines)

    # Now, test the same thing but with an ARC line being the "interruptor."
    # We'll also do this one line earlier, to switch things up.
    glines = reset_glines()
    glines[2] = "ARC\t1\t1\t5"
    assert "Line 3: Node block ends too early." in get_validate_err(glines)


def test_validate_lastgraph_invalid_node_count():
    # Test cases where the specified number of nodes isn't an int value
    glines = reset_glines()
    exp_msg = "Line 1: $NUMBER_OF_NODES must be a positive integer"
    glines[0] = "3.5\t10\t1\t1"
    assert exp_msg in get_validate_err(glines)
    glines[0] = "-3.5\t10\t1\t1"
    assert exp_msg in get_validate_err(glines)
    glines[0] = "-2\t10\t1\t1"
    assert exp_msg in get_validate_err(glines)
    glines[0] = "2.0\t10\t1\t1"
    assert exp_msg in get_validate_err(glines)
    glines[0] = "ABC\t10\t1\t1"
    assert exp_msg in get_validate_err(glines)
    glines[0] = "0x123\t10\t1\t1"
    assert exp_msg in get_validate_err(glines)
    glines[0] = "0\t10\t1\t1"
    assert exp_msg in get_validate_err(glines)


def test_validate_lastgraph_insufficient_node_declaration():
    # Test insufficient node declarations
    glines = reset_glines()
    exp_msg = "Line 5: Node declaration doesn't include enough fields"
    glines[4] = "NODE\t2"
    assert exp_msg in get_validate_err(glines)
    glines[4] = "NODE\t2\t6"
    assert exp_msg in get_validate_err(glines)


def test_validate_lastgraph_invalid_cov_values():
    # Test node declarations where $COV_SHORT1 or $O_COV_SHORT1 are not ints
    glines = reset_glines()
    exp_msg = (
        "Line 5: The $COV_SHORT1 and $O_COV_SHORT1 values must be positive "
        "integers."
    )
    glines[4] = "NODE\t2\t6.0\t20\t5\t0\t0"
    assert exp_msg in get_validate_err(glines)
    glines[4] = "NODE\t2\t6\t20.0\t5\t0\t0"
    assert exp_msg in get_validate_err(glines)
    glines[4] = "NODE\t2\tABC\t20\t5\t0\t0"
    assert exp_msg in get_validate_err(glines)
    glines[4] = "NODE\t2\t6\tABC\t5\t0\t0"
    assert exp_msg in get_validate_err(glines)
    glines[4] = "NODE\t2\tABC\tABC\t5\t0\t0"
    assert exp_msg in get_validate_err(glines)
    glines[4] = "NODE\t2\t-6\t20\t5\t0\t0"
    assert exp_msg in get_validate_err(glines)
    glines[4] = "NODE\t2\t6\t-20\t5\t0\t0"
    assert exp_msg in get_validate_err(glines)
    glines[4] = "NODE\t2\t-6\t-20\t5\t0\t0"
    assert exp_msg in get_validate_err(glines)


def test_validate_lastgraph_invalid_node_id():
    # Test node declarations where the ID starts with a minus sign (-)
    glines = reset_glines()
    glines[1] = "NODE\t-1\t1\t5\t5\t0\t0"
    assert "Line 2: Node IDs can't start with '-'." in get_validate_err(glines)
    glines[1] = "NODE\t-ABC\t1\t5\t5\t0\t0"
    assert "Line 2: Node IDs can't start with '-'." in get_validate_err(glines)
    glines[1] = "NODE\t1\t1\t5\t5\t0\t0"
    glines[4] = "NODE\t-2\t6\t20\t5\t0\t0"
    assert "Line 5: Node IDs can't start with '-'." in get_validate_err(glines)


def test_validate_lastgraph_repeat_node_declaration():
    # Test repeat node declarations
    glines = reset_glines()
    glines[1] = "NODE\t2\t1\t5\t5\t0\t0"
    assert "Line 5: Node ID 2 declared multiple times." in get_validate_err(
        glines
    )
    glines[1] = "NODE\t1\t1\t5\t5\t0\t0"
    glines[4] = "NODE\t1\t6\t20\t5\t0\t0"
    assert "Line 5: Node ID 1 declared multiple times." in get_validate_err(
        glines
    )
    glines[1] = "NODE\tABC\t1\t5\t5\t0\t0"
    glines[4] = "NODE\tABC\t6\t20\t5\t0\t0"
    assert "Line 5: Node ID ABC declared multiple times." in get_validate_err(
        glines
    )


def test_validate_lastgraph_repeat_edge_declaration():
    # previously, these tests failed. but now they should be cool, since we
    # accept multigraphs
    glines = reset_glines()
    glines[7] = "ARC\t2\t1\t5"
    run_validate(glines)

    glines = reset_glines()
    # -1 -> -2 implies 2 -> 1, which is declared after this
    glines[7] = "ARC\t-1\t-2\t5"
    run_validate(glines)

    glines = reset_glines()
    glines[8] = "ARC\t1\t2\t9"
    run_validate(glines)


def test_validate_lastgraph_insufficent_edge_declaration():
    # Test insufficient arc (edge) declarations
    glines = reset_glines()
    exp_msg = "Line 8: Arc declaration doesn't include enough fields."
    glines[7] = "ARC\t1\t2"
    assert exp_msg in get_validate_err(glines)
    glines[7] = "ARC\t1"
    assert exp_msg in get_validate_err(glines)
    glines[7] = "ARC\t"
    assert exp_msg in get_validate_err(glines)


def test_validate_lastgraph_invalid_multiplicity():
    # Test non-integer multiplicity values
    glines = reset_glines()
    exp_msg = (
        "Line 8: The $MULTIPLICITY value of an arc must be a positive integer."
    )
    glines[7] = "ARC\t1\t2\t5.0"
    assert exp_msg in get_validate_err(glines)
    glines[7] = "ARC\t1\t2\tABC"
    assert exp_msg in get_validate_err(glines)


def test_validate_lastgraph_unseen_node_in_edge():
    # Test edges that include non-existent nodes
    glines = reset_glines()
    glines[7] = "ARC\t1\t3\t5"
    assert "Line 8: Unseen node 3" in get_validate_err(glines)
    glines[7] = "ARC\t3\t3\t5"
    assert "Line 8: Unseen node 3" in get_validate_err(glines)
    glines[7] = "ARC\t3\t1\t5"
    assert "Line 8: Unseen node 3" in get_validate_err(glines)
    glines[7] = "ARC\t3\t4\t5"
    assert "Line 8: Unseen node 3" in get_validate_err(glines)
    glines[7] = "ARC\t4\t3\t5"
    assert "Line 8: Unseen node 4" in get_validate_err(glines)
    glines[7] = "ARC\t-4\t3\t5"
    assert "Line 8: Unseen node -4" in get_validate_err(glines)
    # This *should* work, though. Referring to negations of nodes is ok.
    glines[7] = "ARC\t-1\t2\t5"
    run_validate(glines)
    glines[7] = "ARC\t1\t-2\t5"
    run_validate(glines)


def test_validate_lastgraph_inconsistent_node_lengths():
    # Test weird stuff with node lengths being inconsistent
    # 1. forward sequence length doesn't match $COV_SHORT1
    glines = reset_glines()
    glines[2] = "GGAGAGAGA"
    assert (
        "Line 3: Node sequence length doesn't match $COV_SHORT1"
        in get_validate_err(glines)
    )
    glines = reset_glines()
    glines[5] = "GG"
    assert (
        "Line 6: Node sequence length doesn't match $COV_SHORT1"
        in get_validate_err(glines)
    )
    # 2. reverse sequence length doesn't match forward sequence length (and,
    # therefore, $COV_SHORT1)
    glines = reset_glines()
    glines[3] = "GGG"
    assert "Line 4: Node sequences have unequal lengths" in get_validate_err(
        glines
    )


def test_validate_lastgraph_node_ends_at_end_of_file():
    # Test a node ending before the file ends
    glines = reset_glines()
    glines.append("NODE\t3\t1\t5\t5\t0\t0")
    assert "Node block ended too early at end-of-file" in get_validate_err(
        glines
    )
    glines.append("A")
    assert "Node block ended too early at end-of-file" in get_validate_err(
        glines
    )


def test_validate_lastgraph_node_count_mismatch():
    # Test the number of nodes in the file not matching the actual number of
    # nodes
    glines = reset_glines()
    glines[0] = "3\t10\t1\t1"
    assert (
        "indicated that there were 3 node(s), but we identified 2 node(s)"
        in get_validate_err(glines)
    )
    glines[0] = "1\t10\t1\t1"
    assert (
        "indicated that there were 1 node(s), but we identified 2 node(s)"
        in get_validate_err(glines)
    )
