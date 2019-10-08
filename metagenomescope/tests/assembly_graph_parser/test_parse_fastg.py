# from .utils import run_tempfile_test
from metagenomescope.assembly_graph_parser import parse_fastg
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
    assert len(g.nodes) == 6
