import pytest
from metagenomescope import name_utils
from metagenomescope.errors import WeirdError, GraphParsingError


def test_negate():
    assert name_utils.negate("1") == "-1"
    assert name_utils.negate("-3") == "3"
    assert name_utils.negate("20") == "-20"
    assert name_utils.negate("-100") == "100"
    # IDs should be stored as strings -- so we should be able to negate them
    # regardless of if it makes sense mathematically
    assert name_utils.negate("0") == "-0"
    assert name_utils.negate("-0") == "0"
    assert name_utils.negate("contig_id_123") == "-contig_id_123"
    assert name_utils.negate("-contig_id_123") == "contig_id_123"
    assert name_utils.negate("abcdef") == "-abcdef"
    assert name_utils.negate("-abcdef") == "abcdef"


def test_negate_empty():
    with pytest.raises(WeirdError) as ei:
        name_utils.negate("")
    assert "empty node name" in str(ei.value)


def test_negate_str_required():
    with pytest.raises(WeirdError):
        name_utils.negate(123)

    with pytest.raises(WeirdError):
        name_utils.negate(-123)

    with pytest.raises(WeirdError):
        name_utils.negate(0)

    with pytest.raises(WeirdError):
        name_utils.negate(123.45)

    with pytest.raises(WeirdError):
        name_utils.negate(["lmao"])


def test_sanity_check_node_name_simple():
    name_utils.sanity_check_node_name("abcdef")
    name_utils.sanity_check_node_name("123")
    name_utils.sanity_check_node_name("k99_123412")
    name_utils.sanity_check_node_name("hello i am a node")


def test_sanity_check_node_name_empty():
    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("")
    assert str(ei.value) == "A node with an empty name exists in the graph?"


def test_sanity_check_node_name_whitespace_only():
    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("    ")
    assert str(ei.value) == (
        'A node named "    " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )


def test_sanity_check_node_name_whitespace_surrounding():
    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name(" abcdef")
    assert str(ei.value) == (
        'A node named " abcdef" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("hello ")
    assert str(ei.value) == (
        'A node named "hello " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name(" eee ")
    assert str(ei.value) == (
        'A node named " eee " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("what\t")
    assert str(ei.value) == (
        'A node named "what\t" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("\nohno!")
    assert str(ei.value) == (
        'A node named "\nohno!" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )


def test_sanity_check_node_name_splitsuffix_already():
    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("123-L")
    assert str(ei.value) == (
        'A node named "123-L" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )
    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("abcdef-R")
    assert str(ei.value) == (
        'A node named "abcdef-R" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )


def test_sanity_check_node_name_surrounding_whitespace():
    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("123-L")
    assert str(ei.value) == (
        'A node named "123-L" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )
    with pytest.raises(GraphParsingError) as ei:
        name_utils.sanity_check_node_name("abcdef-R")
    assert str(ei.value) == (
        'A node named "abcdef-R" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )
