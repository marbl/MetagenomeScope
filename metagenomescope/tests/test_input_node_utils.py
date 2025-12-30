import pytest
from metagenomescope import input_node_utils
from metagenomescope.errors import WeirdError, GraphParsingError


def test_negate_node_id():
    with pytest.raises(WeirdError) as ei:
        input_node_utils.negate_node_id("")
    assert "empty node name" in str(ei.value)
    assert input_node_utils.negate_node_id("1") == "-1"
    assert input_node_utils.negate_node_id("-3") == "3"
    assert input_node_utils.negate_node_id("20") == "-20"
    assert input_node_utils.negate_node_id("-100") == "100"
    # IDs should be stored as strings -- so we should be able to negate them
    # regardless of if it makes sense mathematically
    assert input_node_utils.negate_node_id("0") == "-0"
    assert input_node_utils.negate_node_id("-0") == "0"
    assert input_node_utils.negate_node_id("contig_id_123") == "-contig_id_123"
    assert input_node_utils.negate_node_id("-contig_id_123") == "contig_id_123"
    assert input_node_utils.negate_node_id("abcdef") == "-abcdef"
    assert input_node_utils.negate_node_id("-abcdef") == "abcdef"


def test_negate_node_id_str_required():
    with pytest.raises(WeirdError):
        input_node_utils.negate_node_id(123)

    with pytest.raises(WeirdError):
        input_node_utils.negate_node_id(-123)

    with pytest.raises(WeirdError):
        input_node_utils.negate_node_id(0)

    with pytest.raises(WeirdError):
        input_node_utils.negate_node_id(123.45)

    with pytest.raises(WeirdError):
        input_node_utils.negate_node_id(["lmao"])


def test_sanity_check_node_name_simple():
    input_node_utils.sanity_check_node_name("abcdef")
    input_node_utils.sanity_check_node_name("123")
    input_node_utils.sanity_check_node_name("k99_123412")
    input_node_utils.sanity_check_node_name("hello i am a node")


def test_sanity_check_node_name_empty():
    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("")
    assert str(ei.value) == "A node with an empty name exists in the graph?"


def test_sanity_check_node_name_whitespace_only():
    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("    ")
    assert str(ei.value) == (
        'A node named "    " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )


def test_sanity_check_node_name_whitespace_surrounding():
    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name(" abcdef")
    assert str(ei.value) == (
        'A node named " abcdef" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("hello ")
    assert str(ei.value) == (
        'A node named "hello " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name(" eee ")
    assert str(ei.value) == (
        'A node named " eee " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("what\t")
    assert str(ei.value) == (
        'A node named "what\t" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("\nohno!")
    assert str(ei.value) == (
        'A node named "\nohno!" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )


def test_sanity_check_node_name_splitsuffix_already():
    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("123-L")
    assert str(ei.value) == (
        'A node named "123-L" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )
    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("abcdef-R")
    assert str(ei.value) == (
        'A node named "abcdef-R" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )


def test_sanity_check_node_name_surrounding_whitespace():
    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("123-L")
    assert str(ei.value) == (
        'A node named "123-L" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )
    with pytest.raises(GraphParsingError) as ei:
        input_node_utils.sanity_check_node_name("abcdef-R")
    assert str(ei.value) == (
        'A node named "abcdef-R" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )
