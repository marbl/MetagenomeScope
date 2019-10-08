from .utils import run_tempfile_test


def get_test_fastg():
    """Just returns a list representation of small.fastg, which is from
    the fedarko/pyfastg repository test code.
    """
    # We could also just open and read the file, but this is easier to look at
    return [
        ">EDGE_1_length_9_cov_4.5:EDGE_3_length_5_cov_16.5';",
        "ATCGCCCAT",
        ">EDGE_1_length_9_cov_4.5':EDGE_2_length_3_cov_100';",
        "ATGGGCGAT",
        ">EDGE_2_length_3_cov_100:EDGE_1_length_9_cov_4.5,EDGE_3_length_5_cov_16.5,EDGE_3_length_5_cov_16.5';",
        "CGA",
        ">EDGE_2_length_3_cov_100';",
        "TCG",
        ">EDGE_3_length_5_cov_16.5:EDGE_1_length_9_cov_4.5',EDGE_2_length_3_cov_100';",
        "GGATC",
        ">EDGE_3_length_5_cov_16.5':EDGE_2_length_3_cov_100';",
        "GATCC",
    ]


def test_good():
    g = run_tempfile_test("fastg", get_test_fastg(), None, None)
    # CODELINK: remaining code in this function is taken from
    # test_parse_small_assembly_graph() in the pyfastg codebase.
    # (...I mean, I literally wrote that function, but might as well cite it?)
    assert len(g.nodes) == 6
    assert len(g.edges) == 8
    i2length = {1: 9, 2: 3, 3: 5}
    i2cov = {1: 4.5, 2: 100, 3: 16.5}
    i2gc = {1: 5 / 9.0, 2: 2 / 3.0, 3: 3 / 5.0}
    for i in range(1, 4):
        si = str(i)
        for suffix in ("+", "-"):
            name = si + suffix
            assert name in g.nodes
            assert g.nodes[name]["cov"] == i2cov[i]
            assert g.nodes[name]["length"] == i2length[i]
            assert g.nodes[name]["gc"] == i2gc[i]

    valid_edges = (
        ("2+", "1+"),
        ("2+", "3-"),
        ("2+", "3+"),
        ("1+", "3-"),
        ("3-", "2-"),
        ("3+", "1-"),
        ("3+", "2-"),
        ("1-", "2-"),
    )
    for e in valid_edges:
        assert e in g.edges
