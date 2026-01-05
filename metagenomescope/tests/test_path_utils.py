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


def test_map_cc_nums_to_paths_simple():
    paths = pu.get_paths_from_agp(
        "metagenomescope/tests/input/scaffolds_ecoli.agp"
    )
    ag = AssemblyGraph("metagenomescope/tests/input/E_coli_LastGraph")
    assert pu.map_cc_nums_to_paths(ag.nodeid2obj, paths) == (
        {3: ["scaffold_1"]},
        {"scaffold_1": 3},
    )
