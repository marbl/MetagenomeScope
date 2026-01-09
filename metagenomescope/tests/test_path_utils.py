import pytest
import tempfile
from metagenomescope.errors import PathParsingError
from metagenomescope.graph import AssemblyGraph
from metagenomescope import path_utils as pu


def test_get_paths_from_agp_simple():
    paths = pu.get_paths_from_agp(
        "metagenomescope/tests/input/scaffolds_ecoli.agp"
    )
    assert paths == {"scaffold_1": ["17", "-35", "-63", "259"]}


def test_paths_from_agp_extra_cols():
    with tempfile.NamedTemporaryFile(suffix=".agp") as fp:
        fp.write(b"scaffold_1\t1\t4033\t0\tW\t17\t1\t4033\t+\thelloimevil\n")
        fp.seek(0)
        with pytest.raises(PathParsingError) as ei:
            pu.get_paths_from_agp(fp.name)
        assert "doesn't have exactly 9 tab-separated columns" in str(ei.value)


def test_paths_from_agp_toofew_cols():
    with tempfile.NamedTemporaryFile(suffix=".agp") as fp:
        fp.write(b"scaffold_1")
        fp.seek(0)
        with pytest.raises(PathParsingError) as ei:
            pu.get_paths_from_agp(fp.name)
        assert "doesn't have exactly 9 tab-separated columns" in str(ei.value)


def test_get_path_maps_simple():
    paths = pu.get_paths_from_agp(
        "metagenomescope/tests/input/scaffolds_ecoli.agp"
    )
    ag = AssemblyGraph("metagenomescope/tests/input/E_coli_LastGraph")
    assert pu.get_path_maps(ag.nodeid2obj, paths) == (
        {3: ["scaffold_1"]},
        {
            "17": {"scaffold_1"},
            "-35": {"scaffold_1"},
            "-63": {"scaffold_1"},
            "259": {"scaffold_1"},
        },
        {"scaffold_1": 3},
    )


def test_get_path_maps_one_missing(caplog):
    ag = AssemblyGraph("metagenomescope/tests/input/E_coli_LastGraph")
    paths = {
        "scaffold_1": ["17", "-35", "-63", "259"],
        "scaff_invis": ["asdf", "ghjk"],
    }
    assert pu.get_path_maps(ag.nodeid2obj, paths) == (
        {3: ["scaffold_1"]},
        {
            "17": {"scaffold_1"},
            "-35": {"scaffold_1"},
            "-63": {"scaffold_1"},
            "259": {"scaffold_1"},
        },
        {"scaffold_1": 3},
    )
    assert caplog.records[0].msg == (
        "    WARNING: 1 / 2 path contained node(s) that were not present in "
        'the graph. This "missing" path will not be shown in the '
        "visualization. Missing path: scaff_invis"
    )


def test_get_path_maps_missing_due_to_single_missing_node(caplog):
    ag = AssemblyGraph("metagenomescope/tests/input/E_coli_LastGraph")
    paths = {
        "scaffold_1": ["17", "-35", "-63", "259"],
        "scaff_invis": ["asdf", "ghjk"],
        "scaffold_2": ["-35", "bruh"],
    }
    assert pu.get_path_maps(ag.nodeid2obj, paths) == (
        {3: ["scaffold_1"]},
        {
            "17": {"scaffold_1"},
            "-35": {"scaffold_1"},
            "-63": {"scaffold_1"},
            "259": {"scaffold_1"},
        },
        {"scaffold_1": 3},
    )
    exp_warning_msg = (
        "    WARNING: 2 / 3 paths contained node(s) that were not present in "
        'the graph. These "missing" paths will not be shown in the '
        "visualization. Missing paths: "
    )
    # The order of the output missing paths is arbitrary (it is not worth
    # the effort to sort them...), so let's accept either possible warning
    # i guess
    assert caplog.records[0].msg in (
        exp_warning_msg + "scaff_invis, scaffold_2",
        exp_warning_msg + "scaffold_2, scaff_invis",
    )


def test_get_path_maps_all_missing():
    ag = AssemblyGraph("metagenomescope/tests/input/E_coli_LastGraph")
    paths = {"scaff_invis": ["asdf", "ghjk"]}
    with pytest.raises(PathParsingError) as ei:
        pu.get_path_maps(ag.nodeid2obj, paths)
    assert str(ei.value) == (
        "All of the paths contained nodes that were not present in the graph. "
        "Please verify that your path and graph files match up."
    )
