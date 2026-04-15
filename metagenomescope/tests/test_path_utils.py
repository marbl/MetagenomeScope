import pytest
import tempfile
from metagenomescope.errors import PathParsingError, UIError
from metagenomescope.graph import AssemblyGraph
from metagenomescope.gap import Gap
from metagenomescope import path_utils as pu


def test_add_rev_if_needed():
    assert pu.add_rev_if_needed("asdf", "+", True) == "asdf"
    assert pu.add_rev_if_needed("asdf", "-", True) == "-asdf"
    assert pu.add_rev_if_needed("asdf", "+", False) == "asdf"
    assert pu.add_rev_if_needed("asdf", "-", False) == "asdf"

    # weird orientations (e.g. the stuff in the AGP specification)
    # are treated as positive i guess
    # hey since youre reading the tests here is a special gift:
    # https://www.youtube.com/watch?v=URtqADoz9uA
    assert pu.add_rev_if_needed("asdf", "glorp", True) == "asdf"
    assert pu.add_rev_if_needed("asdf", "glorp", True) == "asdf"
    assert pu.add_rev_if_needed("asdf", "glorp", False) == "asdf"
    assert pu.add_rev_if_needed("asdf", "glorp", False) == "asdf"


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


def test_get_paths_from_agp_gap():
    paths = pu.get_paths_from_agp(
        "metagenomescope/tests/input/scaffolds_ecoli_with_gaps.agp"
    )
    assert paths == {
        "scaffold_1": [
            "17",
            "-35",
            "-63",
            Gap(length=123456, gaptype="scaffold"),
            "259",
        ]
    }


def test_parse_verkko_tsv_seqname_simple():
    assert pu.parse_verkko_tsv_seqname("asdf+", True) == "asdf"
    assert pu.parse_verkko_tsv_seqname("asdf-", True) == "-asdf"
    assert pu.parse_verkko_tsv_seqname("asdf+", False) == "asdf"
    assert pu.parse_verkko_tsv_seqname("asdf-", False) == "asdf"

    assert pu.parse_verkko_tsv_seqname("c+", True) == "c"
    assert pu.parse_verkko_tsv_seqname("c-", True) == "-c"
    assert pu.parse_verkko_tsv_seqname("c+", False) == "c"
    assert pu.parse_verkko_tsv_seqname("c-", False) == "c"


def test_parse_verkko_tsv_seqname_tooshort():
    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_seqname("+", True)
    assert str(ei.value) == 'Name on path has < 2 characters: "+"'

    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_seqname("-", True)
    assert str(ei.value) == 'Name on path has < 2 characters: "-"'

    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_seqname("a", True)
    assert str(ei.value) == 'Name on path has < 2 characters: "a"'

    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_seqname("", True)
    assert str(ei.value) == 'Name on path has < 2 characters: ""'


def test_parse_verkko_tsv_seqname_noendorientation():
    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_seqname("asdf", True)
    assert str(ei.value) == 'Name on path doesn\'t end with +/-: "asdf"'

    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_seqname("asdf", False)
    assert str(ei.value) == 'Name on path doesn\'t end with +/-: "asdf"'

    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_seqname("asdf?", False)
    assert str(ei.value) == 'Name on path doesn\'t end with +/-: "asdf?"'


def test_parse_verkko_tsv_gap_simple():
    assert pu.parse_verkko_tsv_gap("[N500N]") == Gap(length=500)
    assert pu.parse_verkko_tsv_gap("[N500N:scaff]") == Gap(
        length=500, gaptype="scaff"
    )
    # should we allow this? whatever. if the scaffolder specifies a 0-length
    # gap then who are we to stop it
    assert pu.parse_verkko_tsv_gap("[N0N]") == Gap(length=0)


def test_parse_verkko_tsv_gap_negativelength():
    # there isn't a big deep reason why this raises a UIError instead
    # of a PathParsingError. it boils down to that's what ui_utils.get_num()
    # throws because we typically call that from the UI when checking like
    # font sizes or whatever that the user specifies in the app.
    #
    # um. we could refactor things so that get_num() could throw custom
    # exception types but literally it doesnt matter at all atm sooooo
    with pytest.raises(UIError) as ei:
        pu.parse_verkko_tsv_gap("[N-1N]")
    assert str(ei.value) == "Verkko path gap size must be \u2265 0."


def test_parse_verkko_tsv_gap_extra_colons_ok():
    assert pu.parse_verkko_tsv_gap("[N123456N:asdf:ghjil:ff]") == Gap(
        length=123456, gaptype="asdf:ghjil:ff"
    )
    # i GUESS this technically works but like come on
    assert pu.parse_verkko_tsv_gap("[N123456N::]") == Gap(
        length=123456, gaptype=":"
    )
    assert pu.parse_verkko_tsv_gap("[N123456N:::]") == Gap(
        length=123456, gaptype="::"
    )


def test_parse_verkko_tsv_gap_noendbracket():
    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_gap("[N123456N")
    assert str(ei.value) == 'Gap "[N123456N" does not end with ]'


def test_parse_verkko_tsv_gap_colon_but_noname():
    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_gap("[N123456N:]")
    assert str(ei.value) == 'Empty gap name: "[N123456N:]"'


def test_parse_verkko_tsv_gap_nolength():
    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_gap("[NN]")
    assert str(ei.value) == 'Empty gap length: "[NN]"'

    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_gap("[NN:asdf]")
    assert str(ei.value) == 'Empty gap length: "[NN:asdf]"'


def test_parse_verkko_tsv_gap_length_doesnt_end_in_n():
    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_gap("[N123]")
    assert str(ei.value) == 'Gap length does not end with N: "[N123]"'

    with pytest.raises(PathParsingError) as ei:
        pu.parse_verkko_tsv_gap("[N123:asdf]")
    assert str(ei.value) == 'Gap length does not end with N: "[N123:asdf]"'


def test_get_paths_from_verkko_tsv_simple():
    with tempfile.NamedTemporaryFile(suffix=".tsv") as fp:
        fp.write(b"name\tpath\tassignment\n")
        fp.write(b"p1\t3+,4-,5-,a+,b-\tMAT\n")
        fp.write(b"p2\t6+,4-,5-,a+,b-\tPAT\n")
        fp.seek(0)
        assert pu.get_paths_from_verkko_tsv(fp.name, True) == {
            "p1": ["3", "-4", "-5", "a", "-b"],
            "p2": ["6", "-4", "-5", "a", "-b"],
        }


def test_get_paths_from_verkko_tsv_gaps_onlyonepath():
    with tempfile.NamedTemporaryFile(suffix=".tsv") as fp:
        fp.write(b"name\tpath\tassignment\n")
        fp.write(b"p1\t3+,4-,5-,a+,[N1N],b-\tMAT\n")
        fp.seek(0)
        assert pu.get_paths_from_verkko_tsv(fp.name, True) == {
            "p1": ["3", "-4", "-5", "a", Gap(length=1), "-b"]
        }


def test_get_paths_from_verkko_tsv_only_gaps():
    with tempfile.NamedTemporaryFile(suffix=".tsv") as fp:
        fp.write(b"name\tpath\tassignment\n")
        fp.write(b"p1\t[N100N],[N0N:asdf]\tMAT\n")
        fp.seek(0)
        with pytest.raises(PathParsingError) as ei:
            pu.get_paths_from_verkko_tsv(fp.name, True)
        assert str(ei.value) == "Path p1 only has gaps???"


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


def test_multiple_path_sources_good():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/flye_yeast.gv",
        agp_fp="metagenomescope/tests/input/flye_yeast.agp",
        flye_info_fp="metagenomescope/tests/input/flye_yeast_assembly_info.txt",
    )
    assert len(ag.pathname2ccnum) == 32


def test_multiple_path_sources_duplicate_name():
    with tempfile.NamedTemporaryFile(suffix=".agp") as fp:
        fp.write(b"contig_53\t1\t4033\t0\tW\t17\t1\t4033\t+\n")
        fp.seek(0)
        with pytest.raises(PathParsingError) as ei:
            AssemblyGraph(
                "metagenomescope/tests/input/flye_yeast.gv",
                agp_fp=fp.name,
                flye_info_fp="metagenomescope/tests/input/flye_yeast_assembly_info.txt",
            )
        assert str(ei.value) == "Duplicate path names found between sources?"


def test_flye_path_with_gaps():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/flye_yeast.gv",
        flye_info_fp="metagenomescope/tests/input/flye_yeast_assembly_info.txt",
    )
    assert len(ag.pathname2objnames) == 29
    assert len(ag.pathname2objnamesandgaps) == 29
    # the gap between -34 and 62 is hidden in this internal representation
    assert ag.pathname2objnames["scaffold_34"] == [
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "-56",
        "-55",
        "-34",
        "62",
        "62",
        "62",
        "62",
        "62",
        "62",
        "62",
        "26",
        "-32",
    ]
    assert ag.pathname2objnamesandgaps["scaffold_34"] == [
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "-56",
        "-55",
        "-34",
        Gap(),
        "62",
        "62",
        "62",
        "62",
        "62",
        "62",
        "62",
        "26",
        "-32",
    ]


def test_merge_paths_simple():
    paths = {"p1": ["a", "b", "c"], "p2": ["b"]}
    newpaths = {"p3": ["c", "d"]}
    pu.merge_paths(paths, newpaths)
    assert paths == {"p1": ["a", "b", "c"], "p2": ["b"], "p3": ["c", "d"]}
    # newpaths should be unchanged
    assert newpaths == {"p3": ["c", "d"]}


def test_merge_paths_empty():
    # merge something into nothing
    paths = {}
    newpaths = {"p3": ["c", "d"]}
    pu.merge_paths(paths, newpaths)
    assert paths == {"p3": ["c", "d"]}
    assert newpaths == {"p3": ["c", "d"]}

    # merge nothing into something
    paths2 = {"z": ["x", "y"]}
    newpaths2 = {}
    pu.merge_paths(paths2, newpaths2)
    assert paths2 == {"z": ["x", "y"]}
    assert newpaths2 == {}

    # merge nothing into nothing
    paths3 = {}
    newpaths3 = {}
    pu.merge_paths(paths3, newpaths3)
    assert paths3 == {}
    assert newpaths3 == {}


def test_merge_paths_duplicates():
    paths = {"p3": ["a", "b"]}
    newpaths = {"p3": ["c", "d"]}
    with pytest.raises(PathParsingError) as ei:
        pu.merge_paths(paths, newpaths)
    assert str(ei.value) == "Duplicate path names found between sources?"
