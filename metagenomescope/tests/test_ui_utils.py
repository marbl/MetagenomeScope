from metagenomescope import ui_utils as uu


def test_fmt_qty():
    assert uu.fmt_qty(12345) == "12,345 bp"
    assert uu.fmt_qty(99999999, "bushels") == "99,999,999 bushels"
