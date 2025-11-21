from metagenomescope import ui_utils as uu


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
