from metagenomescope.gap import Gap


def test_gap_str_representations():
    g = Gap()
    assert repr(g) == "Gap(unknown length)"
    assert str(g) == "Gap (unknown length)"

    g2 = Gap(length=12345)
    assert repr(g2) == "Gap(12,345 bp)"
    assert str(g2) == "Gap (12,345 bp)"

    g3 = Gap(gaptype="centromere")
    assert repr(g3) == 'Gap("centromere", unknown length)'
    assert str(g3) == 'Gap ("centromere", unknown length)'

    g4 = Gap(length=12345, gaptype="centromere")
    assert repr(g4) == 'Gap("centromere", 12,345 bp)'
    assert str(g4) == 'Gap ("centromere", 12,345 bp)'


def test_gap_equality():
    g = Gap()
    g2 = Gap()
    assert g == g2
    assert g2 == g

    g3 = Gap(length=12345)
    assert g != g3
    assert g3 != g

    g4 = Gap(gaptype="scaffold")
    assert g != g4
    assert g4 != g
    assert g4 != g3
    assert g3 != g4
