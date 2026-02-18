import pytest
from metagenomescope import name_utils as nu
from metagenomescope.errors import WeirdError, GraphParsingError


def test_negate():
    assert nu.negate("1") == "-1"
    assert nu.negate("-3") == "3"
    assert nu.negate("20") == "-20"
    assert nu.negate("-100") == "100"
    # IDs should be stored as strings -- so we should be able to negate them
    # regardless of if it makes sense mathematically
    assert nu.negate("0") == "-0"
    assert nu.negate("-0") == "0"
    assert nu.negate("contig_id_123") == "-contig_id_123"
    assert nu.negate("-contig_id_123") == "contig_id_123"
    assert nu.negate("abcdef") == "-abcdef"
    assert nu.negate("-abcdef") == "abcdef"


def test_negate_empty():
    with pytest.raises(WeirdError) as ei:
        nu.negate("")
    assert "empty node name" in str(ei.value)


def test_negate_str_required():
    with pytest.raises(WeirdError):
        nu.negate(123)

    with pytest.raises(WeirdError):
        nu.negate(-123)

    with pytest.raises(WeirdError):
        nu.negate(0)

    with pytest.raises(WeirdError):
        nu.negate(123.45)

    with pytest.raises(WeirdError):
        nu.negate(["lmao"])


def test_sanity_check_node_name_simple():
    nu.sanity_check_node_name("abcdef")
    nu.sanity_check_node_name("123")
    nu.sanity_check_node_name("k99_123412")
    nu.sanity_check_node_name("hello i am a node")


def test_sanity_check_node_name_empty():
    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("")
    assert str(ei.value) == "A node with an empty name exists in the graph?"


def test_sanity_check_node_name_whitespace_only():
    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("    ")
    assert str(ei.value) == (
        'A node named "    " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )


def test_sanity_check_node_name_whitespace_surrounding():
    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name(" abcdef")
    assert str(ei.value) == (
        'A node named " abcdef" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("hello ")
    assert str(ei.value) == (
        'A node named "hello " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name(" eee ")
    assert str(ei.value) == (
        'A node named " eee " exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("what\t")
    assert str(ei.value) == (
        'A node named "what\t" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )

    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("\nohno!")
    assert str(ei.value) == (
        'A node named "\nohno!" exists in the graph. Nodes cannot have names '
        "that start or end with whitespace."
    )


def test_sanity_check_node_name_splitsuffix_already():
    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("123-L")
    assert str(ei.value) == (
        'A node named "123-L" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )
    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("abcdef-R")
    assert str(ei.value) == (
        'A node named "abcdef-R" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )


def test_sanity_check_node_name_surrounding_whitespace():
    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("123-L")
    assert str(ei.value) == (
        'A node named "123-L" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )
    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("abcdef-R")
    assert str(ei.value) == (
        'A node named "abcdef-R" exists in the graph. Nodes cannot have names '
        'that end in "-L" or "-R".'
    )


def test_sanity_check_node_name_commas():
    with pytest.raises(GraphParsingError) as ei:
        nu.sanity_check_node_name("123,456")
    assert str(ei.value) == (
        'A node named "123,456" exists in the graph. Nodes cannot have names '
        "that contain commas."
    )


def test_has_leftsplit_suffix():
    assert nu.has_leftsplit_suffix("40-L")
    assert nu.has_leftsplit_suffix("asdf-L")
    assert not nu.has_leftsplit_suffix("asdf-R")
    assert not nu.has_leftsplit_suffix("asdf")
    assert not nu.has_leftsplit_suffix("123")


def test_has_rightsplit_suffix():
    assert nu.has_rightsplit_suffix("40-R")
    assert nu.has_rightsplit_suffix("asdf-R")
    assert not nu.has_rightsplit_suffix("asdf-L")
    assert not nu.has_rightsplit_suffix("asdf")
    assert not nu.has_rightsplit_suffix("123")


def test_has_split_suffix():
    assert nu.has_split_suffix("40-L")
    assert nu.has_split_suffix("40-R")
    assert not nu.has_split_suffix("40")
    assert not nu.has_split_suffix("40-Lpoop")
    assert not nu.has_split_suffix("40-Rpoop")
    assert not nu.has_split_suffix("40-")


def test_get_splitname_base():
    assert nu.get_splitname_base("40-L") == "40"
    assert nu.get_splitname_base("40-R") == "40"

    with pytest.raises(WeirdError) as ei:
        nu.get_splitname_base("40")
    assert str(ei.value) == "Node name 40 does not have a split suffix?"

    with pytest.raises(WeirdError) as ei:
        nu.get_splitname_base("40-")
    assert str(ei.value) == "Node name 40- does not have a split suffix?"

    with pytest.raises(WeirdError) as ei:
        nu.get_splitname_base("40-Lpoop")
    assert str(ei.value) == "Node name 40-Lpoop does not have a split suffix?"


def test_condense_splits():
    assert nu.condense_splits(["asdf", "40-L", "ghkl", "40-R"]) == [
        "40",
        "asdf",
        "ghkl",
    ]
    assert nu.condense_splits(["asdf", "40", "ghkl"]) == ["40", "asdf", "ghkl"]
    assert nu.condense_splits(["40-L", "40-R"]) == ["40"]
    assert nu.condense_splits(["40-L"]) == ["40-L"]
    assert nu.condense_splits(["ghkl", "40-L", "45"]) == ["40-L", "45", "ghkl"]


def test_condense_splits_basenames_ignored():
    # don't call this function with basenames of split nodes!!! see its docs
    assert nu.condense_splits(["40-L", "40-R", "40"]) == ["40", "40"]
    assert nu.condense_splits(["40-L", "40"]) == ["40", "40-L"]
    assert nu.condense_splits(["40-R", "40"]) == ["40", "40-R"]
