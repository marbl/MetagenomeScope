import logging
from collections import defaultdict
from .errors import AGPParsingError


def get_paths_from_agp(agp_fp, orientation_in_name=True):
    """Loads paths from an AGP file.

    Parameters
    ----------
    agp_fp: str
        A path to an AGP file.

    orientation_in_name: bool
        If True, assume that each node / edge name in the path is
        computed based on looking at the orientation column. If it is
        "-", then the sequence name is "-" + the component_id column;
        otherwise, the sequence name is just the component_id column.

        If False, then do not take the orientation column into account
        when computing sequence names.

        Basically the idea here is that, for most graph filetypes, a path
        that traces through node -35 will probably be specified in an AGP
        file as a path through component_id 35 with orientation "-". But
        for some graph filetypes that don't encode orientation in the
        node name (e.g. MetaCarvel GML outputs), the path would instead
        just trace through a node named contig_35 or something, which would
        already have a defined orientation as a saved property of it somewhere.

    Returns
    -------
    paths: defaultdict of str -> list
        Maps path names to a list of sequence names in the path.

    Raises
    ------
    AGPParsingError
        If the file looks invalid.

    Notes
    -----
    We just ignore gap lines (i.e. those where column 5 is equal to N or U).
    This could be improved in the future, if desired.

    References
    ----------
    https://www.ncbi.nlm.nih.gov/genbank/genome_agp_specification/
    """
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
