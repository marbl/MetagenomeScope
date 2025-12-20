from collections import defaultdict
from .errors import AGPParsingError


def get_paths_from_agp(agp_fp):
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
                raise AGPParsingError(
                    f"Line {line} describes a gap. We don't support this yet "
                    "(is anyone generating these kinds of files...?), but "
                    "let us know if you would like us to support this!"
                )
            paths[parts[0]].append(parts[5])
    return paths
