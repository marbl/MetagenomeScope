import logging
from collections import defaultdict
from . import ui_utils
from .errors import PathParsingError


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
        Maps path names to a list of sequence (node or edge) names in the path.

    Raises
    ------
    PathParsingError
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
            parts = line.strip().split("\t")
            if len(parts) != 9:
                raise PathParsingError(
                    f"Line {line} doesn't have exactly 9 tab-separated columns"
                )
            if parts[4] in "NU":
                # like we totally COULD support this but if nobody is
                # using this kind of thing then it's not worth it
                logging.warning(
                    f"    WARNING: Line {line} describes a gap. Currently, "
                    "gaps are ignored in the visualization. However, please "
                    "let us know if you would like us to support visualizing "
                    "them specially."
                )
                continue
            seq_id = parts[5]
            if orientation_in_name and parts[8] == "-":
                seq_id = "-" + seq_id
            paths[parts[0]].append(seq_id)
    return paths


def map_cc_nums_to_paths(id2obj, paths, nodes=True):
    """Returns a mapping of component size ranks -> path names."""
    # in theory i guess a path can traverse the same sequence multiple
    # times? so let's use a set to account for that
    objname2pathnames = defaultdict(set)
    for pathname, path_parts in paths.items():
        for name in path_parts:
            objname2pathnames[name].add(pathname)
    pathname2ccnum = {}

    for obj in id2obj.values():
        if nodes:
            objname = obj.basename
        else:
            objname = obj.data["id"]
        # Is this node or edge present in at least one of the input paths?
        if objname in objname2pathnames:
            # Yes, it is. Go through all paths it is contained in.
            for pathname in objname2pathnames[objname]:
                # Have we already seen this path?
                if pathname in pathname2ccnum:
                    # Have we recorded this path as being in a *different* cc?
                    if pathname2ccnum[pathname] != obj.cc_num:
                        raise PathParsingError(
                            f"Path {pathname} spans multiple components, "
                            f"including #{pathname2ccnum[pathname]:,} and "
                            f"#{obj.cc_num:,}?"
                        )
                else:
                    # We haven't already seen this path, so record what cc it
                    # is in.
                    pathname2ccnum[pathname] = obj.cc_num
            # Okay, we've finished checking this node/edge. Continue on.
            del objname2pathnames[objname]

    noun = "node" if nodes else "edge"
    if len(objname2pathnames) > 0:
        missing_paths = set()
        for missing_obj, unavailable_paths in objname2pathnames.items():
            for p in unavailable_paths:
                # If we saw another object in this path in the graph,
                # then it will already have been assigned a cc num.
                # Clear it out (on the basis that showing only some of a path
                # does not seem reasonable)
                # https://stackoverflow.com/a/15411146
                pathname2ccnum.pop(p, None)
                missing_paths.add(p)

        if len(pathname2ccnum) == 0:
            raise PathParsingError(
                "All of the paths contained {noun}s that were not present in "
                "the graph. Please verify that your path and graph files "
                "match up."
            )

        missing_info = ui_utils.pluralize(len(missing_paths), "path")
        logging.warning(
            f"    WARNING: {len(missing_paths):,} / {len(paths):,} paths "
            f"contained {noun}s that were not present in the graph. "
            "These \"missing\" paths will not be shown in the visualization."
        )

    ccnum2pathnames = defaultdict(list)
    for pathname in pathname2ccnum:
        ccnum2pathnames[pathname2ccnum[pathname]].append(pathname)

    return ccnum2pathnames, pathname2ccnum


def get_available_count_badge_text(num_available, total_num):
    return f"{num_available:,} / {total_num:,}"
