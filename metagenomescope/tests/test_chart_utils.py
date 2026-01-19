import pytest
from metagenomescope import chart_utils as cu
from metagenomescope.errors import WeirdError


def test_get_eqn_parts():
    assert cu.get_eqn_parts(True) == ("n", "Nodes")
    assert cu.get_eqn_parts(False) == ("e", "Edges")


def test_get_total_length_latex_nodes():
    # you can copy this into a latex equation editor online
    # (e.g. https://editor.codecogs.com/) and verify it looks good
    exp = r"\sum_{n \in \text{Nodes}}\text{Length}(n)"
    assert cu.get_total_length_latex(True) == "$" + exp + "$"
    assert cu.get_total_length_latex(True, False) == exp


def test_get_total_length_latex_edges():
    exp = r"\sum_{e \in \text{Edges}}\text{Length}(e)"
    assert cu.get_total_length_latex(False) == "$" + exp + "$"
    assert cu.get_total_length_latex(False, False) == exp


def test_get_weightedavg_cov_latex_nodes():
    exp = (
        # numerator
        r"\dfrac{\sum_{n \in \text{Nodes}}\text{Coverage}(n) "
        r"\times \text{Length}(n)}"
        # denominator
        r"{\sum_{n \in \text{Nodes}}\text{Length}(n)}"
    )
    assert cu.get_weightedavg_cov_latex(True, "cov") == "$" + exp + "$"


def test_get_weightedavg_cov_latex_edges():
    exp = (
        # numerator
        r"\dfrac{\sum_{e \in \text{Edges}}\text{Coverage}(e) "
        r"\times \text{Length}(e)}"
        # denominator
        r"{\sum_{e \in \text{Edges}}\text{Length}(e)}"
    )
    assert cu.get_weightedavg_cov_latex(False, "cov") == "$" + exp + "$"


def test_get_unweightedavg_cov_latex_covs_on_edges_but_nodecentric():
    # basically, this is the metacarvel case (at the moment)
    exp = (
        # numerator
        r"\dfrac{\sum_{e \in \text{Edges}}\text{Bundle Size}(e)}"
        # denominator
        r"{|\text{Edges}|}"
    )
    assert cu.get_unweightedavg_cov_latex(True, "bsize") == "$" + exp + "$"


def test_get_unweightedavg_cov_latex_covs_not_nodecentric():
    with pytest.raises(WeirdError) as ei:
        cu.get_unweightedavg_cov_latex(False, "bsize")
    assert str(ei.value) == "we don't support this yet"


def test_get_plot_missing_data_msg_none():
    assert cu.get_plot_missing_data_msg(0, 100, "asdf", "bruh") is None
    assert cu.get_plot_missing_data_msg(0, 1, "asdf", "bruh") is None


def test_get_plot_missing_data_msg_one():
    msg = cu.get_plot_missing_data_msg(1, 100, "asdf", "bruh")
    assert len(msg) == 2
    # dash html objects don't get along with equality tests so just look at
    # the child strings
    assert msg[0].children == "1 / 100 (1.00%) asdf"
    assert msg[1] == " is omitted from this plot due to bruh."


def test_get_plot_missing_data_msg_two():
    msg = cu.get_plot_missing_data_msg(2, 5, "thing", "being test cases :(")
    assert len(msg) == 2
    assert msg[0].children == "2 / 5 (40.00%) things"
    assert msg[1] == " are omitted from this plot due to being test cases :(."
