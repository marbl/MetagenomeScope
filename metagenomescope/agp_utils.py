import logging
from collections import defaultdict
from .errors import AGPParsingError


def get_paths_from_agp(agp_fp, orientation_in_name=True):
    # https://www.ncbi.nlm.nih.gov/genbank/genome_agp_specification/
    paths = defaultdict(list)
    with open(agp_fp, "r") as fh:
        for line in fh:
            parts = line.split("\t")
            if len(parts) != 9:
                raise AGPParsingError(
                    f"Line {line} doesn't have exactly 9 tab-separated columns"
                )
            if parts[4] in "NU":
                # like we totally COULD support this but if nobody is
                # using this kind of thing then it's not worth it
                logging.warning(
                    f"Line {line} describes a gap. Currently, gaps are "
                    "ignored in the visualization. However, please let us "
                    "know if you would like us to support visualizing them "
                    "specially."
                )
                continue
            seq_id = parts[5]
            if parts[8] == "-":
                seq_id = "-" + seq_id
            paths[parts[0]].append(seq_id)
    return paths
