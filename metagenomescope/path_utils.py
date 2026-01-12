import logging
import pandas as pd
from collections import defaultdict
from metagenomescope import config
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
        "-", then the sequence name is config.REV + the component_id column;
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
            # NOTE: ok look, config.REV == "-", so whatever. But the AGP
            # specification specifically writes out a minus sign, so i guess
            # in theory we can change config.REV/FWD without breaking this
            # function. sure. look it really doesn't matter im never gonna
            # change those LOL
            if orientation_in_name and parts[8] == "-":
                seq_id = config.REV + seq_id
            paths[parts[0]].append(seq_id)
    return paths


def get_paths_from_flye_info(fp):
    df = pd.read_csv(fp, sep="\t", index_col=0)
    if "graph_path" not in df.columns:
        raise PathParsingError("graph_path column not in assembly_info file?")
    paths = df["graph_path"].str.split(",").to_dict()
    trimmedpaths = {}
    seen_gaps = False
    for name, edgeids in paths.items():
        if name in trimmedpaths:
            raise PathParsingError(
                f"Name {name} occurs twice in assembly_info file?"
            )
        eids = []
        for i in paths[name]:
            if i == "*":
                continue
            elif i == "??":
                seen_gaps = True
            else:
                eids.append(i)
        if len(eids) == 0:
            raise PathParsingError(f"Invalid path: {name} -> {paths[name]}")
        trimmedpaths[name] = eids
    if seen_gaps:
        logging.warning(
            "    Found gaps in the assembly_info file. Currently we ignore "
            "gaps in the visualization."
        )
    return trimmedpaths


def get_path_maps(id2obj, paths, nodes=True):
    """Creates mappings between component size ranks and path names.

    Parameters
    ----------
    id2obj: dict of str -> (Node or Edge)
        Maps node or edge IDs to Node / Edge objects in the graph. This should
        only contain nodes (if nodes=True) or edges (if edges=True).

    paths: dict of str -> list
        Maps path name to the names of nodes or edges within the path. The
        names contained these lists should only be of nodes or edges, depending
        again on what "nodes" is set to.

        Note that we expect node names here to correspond to the .basename
        attributes of Node objects in the graph, and we expecte edge names
        here to correspond to the .data["id"] attributes of Edge objects (the
        exact behavior is governed by Edge.get_userspecified_id()).

    nodes: bool
        If True, assume the paths are on nodes. If False, assume the paths
        are on edges.

    Returns
    -------
    ccnum2pathnames, objname2pathnames, pathname2ccnum: (
        dict of int -> list, dict of str -> set, dict of str -> int
    )
        The first dict maps component size rank to a list of the names of all
        paths in this component.

        The second dict maps node or edge "names" (as given in the paths
        input above) to a set of the names of all paths that traverse this
        node or edge. (Yes, a set, because a path might traverse a node/edge
        multiple times.)

        The third dict is the inverse of the first: it maps each path name
        to its parent component size rank.

        Note that some input paths may not be represented in these dicts. If
        a path contains at least one node or edge name that is not in the graph
        at all, then we will not include this path in any of these dicts.
        If literally no paths meet this criteria then we'll raise an error (see
        below), but as long as one path is "fully represented" then this
        function should not raise an error. (It will emit a warning about these
        "missing" paths, though.)

    Raises
    ------
    PathParsingError
        If any path contains objects within multiple components.

        If none of the paths are fully represented in the graph.

    Notes
    -----
    It should be possible to speed this up (at least when the graph is
    node-centric) by using the AssemblyGraph.nodename2objs mapping to
    directly look up node objects (rather than having to go through
    .nodeid2obj). However, this is not a bottleneck or anything as is.
    """
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
            objname = obj.get_userspecified_id()
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
    # If a node/edge remains in objname2pathnames at this point, then it
    # means that this object is described in at least one path BUT not
    # present in the actual graph.
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
                f"All of the paths contained {noun}s that were not present in "
                "the graph. Please verify that your path and graph files "
                "match up."
            )

        # we devote probably too much effort to making this warning fancy
        first20_missing_paths = list(missing_paths)[:20]
        pn = "paths"
        suffix = ""
        tmp = 'These "missing" paths'
        # If thousands of paths are missing then don't list all of them, since
        # that will frustrate the user and mess up their terminal. Just list
        # at most 20 missing paths (the choice of which are shown is arbitrary)
        if len(missing_paths) > 20:
            suffix = ", ..."
            mpn = "Some example missing paths"
        elif len(missing_paths) == 1:
            mpn = "Missing path"
            pn = "path"
            tmp = 'This "missing" path'
        else:
            mpn = "Missing paths"
        exampletext = f"{mpn}: {', '.join(first20_missing_paths)}{suffix}"
        logging.warning(
            f"    WARNING: {len(missing_paths):,} / {len(paths):,} {pn} "
            f"contained {noun}(s) that were not present in the graph. "
            f"{tmp} will not be shown in the visualization. {exampletext}"
        )
        if len(objname2pathnames) < 20:
            pretty = ""
            for o in objname2pathnames:
                if len(pretty) > 0:
                    pretty += "; "
                plist = ", ".join(objname2pathnames[o])
                pretty += f"{o} -> {plist}"
            logging.warning(f"    Missing {noun}(s), for reference: {pretty}")

    ccnum2pathnames = defaultdict(list)
    # while we're at it, recreate the mapping of object names to path names
    # (for nodes these are basenames, e.g. "40" instead of "40-L" or "40-R").
    # a big distinction here is that now we have filtered out missing paths,
    # which is why we don't just reuse the earlier version of this mapping
    # that we created.
    #
    # (... not to imply that this could not be made more efficient bc it totes
    # could, this is lazy and i'm tired)
    #
    # also, again, we use a set here just in case a path traverses an obj
    # multiple times
    objname2pathnames = defaultdict(set)
    for pathname in pathname2ccnum:
        ccnum2pathnames[pathname2ccnum[pathname]].append(pathname)
        for objname in paths[pathname]:
            objname2pathnames[objname].add(pathname)

    return ccnum2pathnames, objname2pathnames, pathname2ccnum


def get_available_count_badge_text(num_available, total_num):
    return f"{num_available:,} / {total_num:,}"


def merge_paths(curr_paths, new_paths):
    i0 = set(curr_paths.keys())
    i1 = set(new_paths.keys())
    if i0 & i1:
        raise PathParsingError("Duplicate paths found between sources?")
    curr_paths.update(new_paths)
