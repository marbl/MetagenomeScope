import pytest
from metagenomescope import ui_utils as uu, config, css_config
from metagenomescope.graph import AssemblyGraph
from metagenomescope.errors import UIError, WeirdError


def test_pluralize():
    assert uu.pluralize(1) == "1 edge"
    assert uu.pluralize(1, "node") == "1 node"
    assert uu.pluralize(2) == "2 edges"
    assert uu.pluralize(2, "node") == "2 nodes"
    assert uu.pluralize(0, "node") == "0 nodes"
    assert uu.pluralize(123456, "node") == "123,456 nodes"


def test_fmt_qty():
    assert uu.fmt_qty(12345) == "12,345 bp"
    assert uu.fmt_qty(99999999, "bushels") == "99,999,999 bushels"
    assert uu.fmt_qty(None, "bushels") == "N/A"
    assert uu.fmt_qty(None, "bushels", na="lmao") == "lmao"


def test_decr_size_rank_simple():
    assert uu.decr_size_rank(-2, 1, 5) == 1
    assert uu.decr_size_rank(-1, 1, 5) == 1
    assert uu.decr_size_rank(0, 1, 5) == 1
    # begin "valid" current size ranks
    assert uu.decr_size_rank(1, 1, 5) == 1
    assert uu.decr_size_rank(2, 1, 5) == 1
    assert uu.decr_size_rank(3, 1, 5) == 2
    assert uu.decr_size_rank(4, 1, 5) == 3
    assert uu.decr_size_rank(5, 1, 5) == 4
    # end "valid" current size ranks
    assert uu.decr_size_rank(6, 1, 5) == 5
    assert uu.decr_size_rank(7, 1, 5) == 5
    assert uu.decr_size_rank(8, 1, 5) == 5


def test_decr_size_rank_only1():
    assert uu.decr_size_rank(-2, 1, 1) == 1
    assert uu.decr_size_rank(-1, 1, 1) == 1
    assert uu.decr_size_rank(0, 1, 1) == 1
    assert uu.decr_size_rank(1, 1, 1) == 1
    assert uu.decr_size_rank(5, 1, 1) == 1


def test_incr_size_rank_simple():
    assert uu.incr_size_rank(0, 1, 5) == 1
    # begin "valid" current size ranks
    assert uu.incr_size_rank(1, 1, 5) == 2
    assert uu.incr_size_rank(2, 1, 5) == 3
    assert uu.incr_size_rank(3, 1, 5) == 4
    assert uu.incr_size_rank(4, 1, 5) == 5
    assert uu.incr_size_rank(5, 1, 5) == 5
    # end "valid" current size ranks
    assert uu.incr_size_rank(6, 1, 5) == 5
    assert uu.incr_size_rank(7, 1, 5) == 5
    assert uu.incr_size_rank(8, 1, 5) == 5


def test_incr_size_rank_only1():
    assert uu.incr_size_rank(-2, 1, 1) == 1
    assert uu.incr_size_rank(-1, 1, 1) == 1
    assert uu.incr_size_rank(0, 1, 1) == 1
    assert uu.incr_size_rank(1, 1, 1) == 1
    assert uu.incr_size_rank(5, 1, 1) == 1


def test_get_size_ranks_empty():
    exp_msg = (
        "No component size rank(s) specified. Each entry must be either a "
        'single number (e.g. "1"), a range of numbers (e.g. "2 - 5"), or a '
        'half-open range of numbers (e.g. "2 -").'
    )
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("", 5)
    assert str(ei.value) == exp_msg

    with pytest.raises(UIError) as ei:
        uu.get_size_ranks(None, 5)
    assert str(ei.value) == exp_msg


def test_get_size_ranks_justone():
    assert uu.get_size_ranks("1", 1) == {1}
    assert uu.get_size_ranks("1", 2) == {1}
    assert uu.get_size_ranks("5", 10) == {5}


def test_get_size_ranks_justone_outofrange():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("2", 1)
    # test the untestable... rah rah fight the power
    assert str(ei.value) == (
        'Invalid component size rank "2" specified. The graph only '
        "has 1 component. How did you even get here?"
    )


def test_get_size_ranks_simple():
    assert uu.get_size_ranks("1, 3, 5, 9, 10, 11, 12, 15", 20) == {
        1,
        3,
        5,
        9,
        10,
        11,
        12,
        15,
    }


def test_get_size_ranks_poundsigns():
    assert uu.get_size_ranks("1, 3, #5, 9, 10, 11, #12, 15", 20) == {
        1,
        3,
        5,
        9,
        10,
        11,
        12,
        15,
    }


def test_get_size_ranks_outofrange():
    assert uu.get_size_ranks("1, 3, 5, 9, 10, 11, 12, 15", 15) == {
        1,
        3,
        5,
        9,
        10,
        11,
        12,
        15,
    }

    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("1, 3, 5, 9, 10, 11, 12, 15", 14)
    assert str(ei.value) == (
        'Invalid component size rank "15" specified. Must be in the '
        "range 1 \u2013 14."
    )


def test_get_size_ranks_range_simple():
    assert uu.get_size_ranks("1-3", 5) == {1, 2, 3}
    assert uu.get_size_ranks("1-5", 5) == {1, 2, 3, 4, 5}
    assert uu.get_size_ranks("2, 4-5", 5) == {2, 4, 5}


def test_get_size_ranks_range_halfopen():
    assert uu.get_size_ranks("1-", 5) == {1, 2, 3, 4, 5}
    assert uu.get_size_ranks("2-", 5) == {2, 3, 4, 5}
    assert uu.get_size_ranks("3-", 5) == {3, 4, 5}
    assert uu.get_size_ranks("4-", 5) == {4, 5}
    assert uu.get_size_ranks("5-", 5) == {5}

    assert uu.get_size_ranks("-5", 5) == {1, 2, 3, 4, 5}
    assert uu.get_size_ranks("-4", 5) == {1, 2, 3, 4}
    assert uu.get_size_ranks("-3", 5) == {1, 2, 3}
    assert uu.get_size_ranks("-2", 5) == {1, 2}
    assert uu.get_size_ranks("-1", 5) == {1}


def test_get_size_ranks_range_trivial():
    # supporting these isn't all that important, but i guess they make
    # some stuff with half-open ranges (e.g. "-1") work more naturally so sure
    assert uu.get_size_ranks("1-1", 5) == {1}
    assert uu.get_size_ranks("2-2", 5) == {2}
    assert uu.get_size_ranks("3-3", 5) == {3}
    assert uu.get_size_ranks("4-4", 5) == {4}
    assert uu.get_size_ranks("5-5", 5) == {5}


def test_get_size_ranks_range_outofbounds_high():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("1-5", 3)
    assert str(ei.value) == (
        'Invalid component size rank "5" in the range "1-5" specified. Must '
        "be in the range 1 \u2013 3."
    )


def test_get_size_ranks_range_outofbounds_low():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("0-3", 3)
    assert str(ei.value) == (
        'Invalid component size rank "0" in the range "0-3" specified. Must '
        "be in the range 1 \u2013 3."
    )


def test_get_size_ranks_range_outofbounds_both():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("0-5", 3)
    assert str(ei.value) == (
        'Invalid component size ranks "0" and "5" in the range "0-5" '
        "specified. Both must be in the range 1 \u2013 3."
    )


def test_get_size_ranks_range_backwards():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("3-1", 3)
    assert str(ei.value) == (
        'Invalid component size rank range "3-1" specified. The end should be '
        "bigger than the start."
    )


def test_get_size_ranks_repeated_dashes():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("1--3", 3)
    assert str(ei.value) == (
        'Invalid component size rank range "1--3" specified. The "-" occurs '
        "multiple times?"
    )


def test_get_size_ranks_multiple_dashes():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("1\u2013-3", 3)
    assert str(ei.value) == (
        'Invalid component size rank range "1\u2013-3" specified. Multiple '
        "dash characters present?"
    )


def test_get_size_ranks_just_a_dash():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("-", 3)
    assert str(ei.value) == (
        'Invalid component size rank range "-" specified. Please give a '
        "start and/or an end for the range."
    )


def test_get_size_ranks_gibberish():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("asodfiasodfijasdoifj adfpqow", 3)
    assert str(ei.value) == (
        'Invalid component size rank "asodfiasodfijasdoifj adfpqow" '
        'specified. Must be either a single number (e.g. "1"), a range of '
        'numbers (e.g. "2 - 3"), or a half-open range of numbers (e.g. "2 -").'
    )


def test_get_size_ranks_gibberish_uppercc_varieswithnumccs():
    # as of writing it should be num ccs - 1, unless the graph has exactly
    # two components, in which case it is just 2 (aka num ccs).
    #
    # I guess the idea is we wanna like illustrate why ranges are useful
    # and to show that we can use something that ISN'T the number of ccs
    # since the range of 1 to num ccs is equivalent to just drawing all
    # ccs at once
    #
    # idk i'm probably overthinking this
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("asodfiasodfijasdoifj adfpqow", 2)
    assert str(ei.value) == (
        'Invalid component size rank "asodfiasodfijasdoifj adfpqow" '
        'specified. Must be either a single number (e.g. "1"), a range of '
        'numbers (e.g. "1 - 2"), or a half-open range of numbers (e.g. "1 -").'
    )

    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("asodfiasodfijasdoifj adfpqow", 20)
    assert str(ei.value) == (
        'Invalid component size rank "asodfiasodfijasdoifj adfpqow" '
        'specified. Must be either a single number (e.g. "1"), a range of '
        'numbers (e.g. "2 - 20"), or a half-open range of numbers '
        '(e.g. "2 -").'
    )


def test_get_size_ranks_gibberish_justone():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("asodfiasodfijasdoifj adfpqow", 1)
    assert str(ei.value) == (
        'Invalid component size rank "asodfiasodfijasdoifj adfpqow" '
        "specified. Literally it can only be 1. How did you get here lol"
    )


def test_get_size_ranks_poundsign_in_ranges():
    assert uu.get_size_ranks("#1-#9", 30) == {1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert uu.get_size_ranks("1-#9", 30) == {1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert uu.get_size_ranks("#1-9", 30) == {1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert uu.get_size_ranks("#1 - 9", 30) == {1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert uu.get_size_ranks("#1 - #9", 30) == {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_get_size_ranks_fancydashes_ok():
    # currently controlled by ui_config.RANGE_DASHES. that being said i doubt
    # there are a lot of other people out there who bust out the
    # ctrl-shift-U + 2013 when they want to write numeric ranges so PROBABLY
    # nobody else will use this (unless we implement the whole copying-labels-
    # from-treemap thing)
    assert uu.get_size_ranks("1 - 9", 30) == {1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert uu.get_size_ranks("1 \u2013 9", 30) == {1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert uu.get_size_ranks("1 \u2014 9", 30) == {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_get_size_ranks_range_gibberish():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("asdf - 9", 30)
    assert str(ei.value) == (
        'Invalid component size rank "asdf" in the range "asdf - 9" '
        "specified. Must be in the range 1 \u2013 30."
    )

    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("8 - ghjkl", 30)
    assert str(ei.value) == (
        'Invalid component size rank "ghjkl" in the range "8 - ghjkl" '
        "specified. Must be in the range 1 \u2013 30."
    )

    with pytest.raises(UIError) as ei:
        uu.get_size_ranks("asdf - ghjkl", 30)
    assert str(ei.value) == (
        'Invalid component size ranks "asdf" and "ghjkl" in the range '
        '"asdf - ghjkl" specified. Both must be in the range 1 \u2013 30.'
    )


def test_get_size_ranks_repeated_stuff_okay():
    # shoutout to python sets
    assert uu.get_size_ranks("1-5,3-9,12,15,4,5", 15) == {
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        12,
        15,
    }


def test_get_size_ranks_singlerank_repeats():
    assert uu.get_size_ranks("6, 6,    6, 6, 2, 6, 10", 11) == {2, 6, 10}


def test_get_size_ranks_empty_entries_ok():
    assert uu.get_size_ranks("6,6,,2,,,,,10", 11) == {2, 6, 10}
    assert uu.get_size_ranks(",,,,,, ,,,    ,,,,  1", 11) == {1}


def test_get_size_ranks_just_empty_entries_fails():
    with pytest.raises(UIError) as ei:
        uu.get_size_ranks(",,,,,, ,,,    ,,,, ", 11)
    assert str(ei.value) == (
        "No component size rank(s) specified. Each entry must be either a "
        'single number (e.g. "1"), a range of numbers (e.g. "2 - 11"), or a '
        'half-open range of numbers (e.g. "2 -").'
    )


def test_get_range_text():
    assert uu._get_range_text([3]) == "#3"
    assert uu._get_range_text([1234]) == "#1,234"
    assert (
        uu._get_range_text([1234, 1235, 1236, 1237]) == "#1,234 \u2013 1,237"
    )

    # this should never happen in practice, but since _get_range_text() assumes
    # that the input range is continuous it doesn't (currently) bother checking
    assert uu._get_range_text([1234, 1235, 999999]) == "#1,234 \u2013 999,999"
    assert uu._get_range_text([1234, 1235, 999999]) == "#1,234 \u2013 999,999"


def test_fmt_num_ranges():
    assert uu.fmt_num_ranges([3]) == "#3"
    assert uu.fmt_num_ranges([1234]) == "#1,234"
    # test case where the final element is "isolated"
    assert uu.fmt_num_ranges([1234, 1235, 1237]) == (
        "#1,234 \u2013 1,235; #1,237"
    )
    # test case where the final element is part of a continuous range
    assert uu.fmt_num_ranges([1, 10, 100, 222, 223, 300, 301]) == (
        "#1; #10; #100; #222 \u2013 223; #300 \u2013 301"
    )
    # verify sorting is done for us
    assert uu.fmt_num_ranges([300, 10, 100, 222, 223, 1, 301]) == (
        "#1; #10; #100; #222 \u2013 223; #300 \u2013 301"
    )
    # duplicate entries are split off into their own ranges, depending
    # on what entries they are surrounded by in the sorted list.
    # look this should never happen in practice anyway.
    assert uu.fmt_num_ranges([1, 2, 3, 3, 3, 4]) == (
        "#1 \u2013 3; #3; #3 \u2013 4"
    )


def test_get_curr_drawn_text_all_multicc():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert (
        uu.get_curr_drawn_text({"draw_type": config.DRAW_ALL}, ag)
        == "#1 \u2013 4"
    )


def test_get_curr_drawn_text_all_1cc():
    ag = AssemblyGraph("metagenomescope/tests/input/one.gml")
    assert uu.get_curr_drawn_text({"draw_type": config.DRAW_ALL}, ag) == "#1"


def test_get_curr_drawn_text_cc_single():
    ag = AssemblyGraph("metagenomescope/tests/input/one.gml")
    assert (
        uu.get_curr_drawn_text(
            {"draw_type": config.DRAW_CCS, "cc_nums": [1]}, ag
        )
        == "#1"
    )

    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert (
        uu.get_curr_drawn_text(
            {"draw_type": config.DRAW_CCS, "cc_nums": [3]}, ag
        )
        == "#3"
    )


def test_get_curr_drawn_text_cc_multi():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert (
        uu.get_curr_drawn_text(
            {"draw_type": config.DRAW_CCS, "cc_nums": [3, 1, 4]}, ag
        )
        == "#1; #3 \u2013 4"
    )


def test_get_curr_drawn_text_around():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    n0 = ag.nodeid2obj[0]
    n1 = ag.nodeid2obj[1]
    names = ", ".join(sorted((n0.name, n1.name)))
    assert (
        uu.get_curr_drawn_text(
            {
                "draw_type": config.DRAW_AROUND,
                "around_node_ids": [0, 1],
                "around_dist": 0,
            },
            ag,
        )
        == f"around nodes {names} (distance 0)"
    )


def test_get_curr_drawn_text_bad_draw_type():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    with pytest.raises(WeirdError) as ei:
        uu.get_curr_drawn_text({"draw_type": "hullabaloo"}, ag)
    assert str(ei.value) == "Unrecognized draw type: hullabaloo"


def test_get_node_names():
    assert uu.get_node_names("1,2,3,node_5,  abc,,,3,node_6, node_5") == {
        "1",
        "2",
        "3",
        "node_5",
        "abc",
        "node_6",
    }
    assert uu.get_node_names("node_1") == {"node_1"}
    assert uu.get_node_names("3") == {"3"}
    assert uu.get_node_names("4,,,,  ,,,,,,4,") == {"4"}


def test_get_node_names_empty():
    exp_err = "No node name(s) specified."

    with pytest.raises(UIError) as ei:
        uu.get_node_names(None)
    assert str(ei.value) == exp_err

    with pytest.raises(UIError) as ei:
        uu.get_node_names("")
    assert str(ei.value) == exp_err

    with pytest.raises(UIError) as ei:
        uu.get_node_names("         \t ")
    assert str(ei.value) == exp_err

    with pytest.raises(UIError) as ei:
        uu.get_node_names("         \t ")
    assert str(ei.value) == exp_err


def test_get_node_names_just_empty_entries():
    exp_err = "No node name(s) specified."

    with pytest.raises(UIError) as ei:
        uu.get_node_names(",,,,,,,,,,,")
    assert str(ei.value) == exp_err

    with pytest.raises(UIError) as ei:
        uu.get_node_names(",,,,,,,,,     ,,")
    assert str(ei.value) == exp_err

    with pytest.raises(UIError) as ei:
        uu.get_node_names(",")
    assert str(ei.value) == exp_err


def test_get_badge_color():
    assert uu.get_badge_color(0) == css_config.BADGE_ZERO_COLOR
    assert (
        uu.get_badge_color(0, selection_only=False)
        == css_config.BADGE_ZERO_COLOR
    )
    assert uu.get_badge_color(1) == css_config.BADGE_SELECTED_COLOR
    assert (
        uu.get_badge_color(1, selection_only=False)
        == css_config.BADGE_AVAILABLE_COLOR
    )
