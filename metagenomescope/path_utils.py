import logging
import pandas as pd
from collections import defaultdict
from metagenomescope import config, ui_utils
from .errors import PathParsingError
from .gap import Gap


def add_rev_if_needed(name, orientation, orientation_in_name):
    """Converts a name and orientation to the expected name format.

    Parameters
    ----------
    name: str
        Node / edge name (ignoring orientation), e.g. "contig5".

    orientation: str
        Probably either "+" or "-". This can theoretically be other stuff
        (https://www.ncbi.nlm.nih.gov/genbank/genome_agp_specification/)
        but we will treat everything that isn't "-" as if it was just "+".

    orientation_in_name: bool
        If True, reverse-orientation sequence names are prefixed with
        config.REV (e.g. "-contig5"). Forward-orientation sequence names
        are not prefixed with anything (e.g. "contig5").

        If False, orientations don't go in the name at all -- rather than
        having pairs like "-contig5" and "contig5", we now assume there is
        just one copy of each sequence with a predefined orientation. This
        is the case for MetaCarvel GML files.

    Returns
    -------
    name: str

    Notes
    -----
    In practice, config.REV == "-", so whatever. I guess there is some value
    in keeping "-" (what we expect to see in AGP files, Verkko TSV files, etc)
    separate from config.REV, but probably config.REV will never be changed so
    it's nbd
    """
    if orientation_in_name and orientation == "-":
        return config.REV + name
    else:
        return name


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
    paths: defaultdict of str -> list of str or Gap
        Maps path names to a list of sequence (node or edge) names in the path.
        Gaps are represented as Gap objects in the list.

    Raises
    ------
    PathParsingError or UIError
        If the file looks invalid.

    Notes
    -----
    There is more info we can extract from AGP files about gaps (e.g. linkage,
    linkage_evidence) if desired.

    References
    ----------
    https://www.ncbi.nlm.nih.gov/genbank/genome_agp_specification/
    """
    paths = defaultdict(list)
    pathnames_with_nongaps = set()
    with open(agp_fp, "r") as fh:
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) != 9:
                raise PathParsingError(
                    f"Line {line} doesn't have exactly 9 tab-separated columns"
                )
            path_name = parts[0]
            if parts[4] in "NU":
                if parts[4] == "N":
                    # delegate checking that this is a valid integer to utils
                    glen = ui_utils.get_num(parts[5], "AGP path gap length")
                else:
                    glen = None
                paths[path_name].append(Gap(length=glen, gaptype=parts[6]))
                continue
            seq_id = add_rev_if_needed(parts[5], parts[8], orientation_in_name)
            paths[path_name].append(seq_id)
            pathnames_with_nongaps.add(path_name)
    only_gap_paths = set(paths.keys()) - pathnames_with_nongaps
    if only_gap_paths:
        raise PathParsingError(f"Some paths only have gaps: {only_gap_paths}")
    return paths


def get_paths_dict_from_tsv(fp, path_col):
    """Extracts path info from a column in a tab-separated file.

    Parameters
    ----------
    fp: str
        Path to a TSV file. There is a lot of leeway in how this file is
        formatted -- the only requirements are that:

        1. it is a tab-separated file
        2. it has a header row
        3. the leftmost column has the path names
        4. one of the other columns describes the contents of each path,
           which are comma-separated entries

    path_col: str
        Column name for requirement #4 above.

    Raises
    ------
    PathParsingError
        If a column named path_col is not in the file, if any path occurs
        more than once in the file, or if the file does not describe any
        paths.

    Other stuff (e.g. FileNotFoundError)
        Could be raised by pd.read_csv() if the file is missing, malformed,
        etc.

    Notes
    -----
    In theory this is all stuff we could do without using pandas. Their CSV
    reading functions are pretty solid in my experience but if we REALLY have
    a bottleneck here then we can do this all manually, maybe
    """
    # treat even empty cells as strings: https://stackoverflow.com/a/67350928
    df = pd.read_csv(fp, sep="\t", index_col=0, dtype=str, na_filter=False)

    if path_col not in df.columns:
        raise PathParsingError(f'Column "{path_col}" not in {fp}.')

    if len(df.index) == 0:
        raise PathParsingError(f"{fp} does not describe any paths.")

    # raise an error if any path occurs more than once on a row
    # https://stackoverflow.com/a/20076611
    # the first row has the most frequently occurring thing, so we
    # can just check the count for the first row in value_counts()
    # NOTE: I am sure this could be made faster by just iterating through
    # the df and exiting as soon as we see something occurring twice. however,
    # 99% of the time that will never happen everything will occur just once
    sorted_paths_by_ct = df.index.value_counts()
    if sorted_paths_by_ct.iloc[0] > 1:
        p = sorted_paths_by_ct.index[0]
        raise PathParsingError(f'Path "{p}" occurs multiple times in {fp}.')

    return df[path_col].str.split(",").to_dict()


def parse_verkko_tsv_seqname(nametext, orientation_in_name=True):
    """Parses a node / edge name from an entry in a Verkko path.

    Parameters
    ----------
    nametext: str
        Looks something like "utig4-1024-".

    orientation_in_name: bool
        See get_paths_from_agp().

    Returns
    -------
    str

    Raises
    ------
    PathParsingError
        If the name looks invalid.
    """
    if len(nametext) < 2:
        raise PathParsingError(
            f'Name on path has < 2 characters: "{nametext}"'
        )
    lastchar = nametext[-1]
    if lastchar not in "-+":
        raise PathParsingError(
            f'Name on path doesn\'t end with +/-: "{nametext}"'
        )
    return add_rev_if_needed(nametext[:-1], lastchar, orientation_in_name)


def parse_verkko_tsv_gap(gaptext):
    """Extracts gap length and (if given) gap type from a gap in a Verkko path.

    Parameters
    ----------
    gaptext: str
        Looks something like "[N500N:scaffold]".
        We assume that this starts with config.VERKKO_PATH_GAP_PREFIX ("[N").

    Returns
    -------
    metagenomescope.gap.Gap

    Raises
    ------
    PathParsingError or UIError
        If the gap text looks invalid.
    """
    if not gaptext.endswith("]"):
        raise PathParsingError(f'Gap "{gaptext}" does not end with ]')

    GAP_PREFIX_LEN = len(config.VERKKO_PATH_GAP_PREFIX)
    gaptype = None
    if ":" in gaptext:
        # Gap looks like "[N500N:scaffold]"; slice to just "[N500N"
        # note that this is perfectly okay with there being multiple ":"s.
        # we assume that the first one indicates the start of the gap type,
        # and allow arbitrarily many ";"s in the gap type afterwards
        lengthpartendpos = gaptext.index(":")
        if len(gaptext) - lengthpartendpos > 2:
            gaptype = gaptext[lengthpartendpos + 1 : -1]
        else:
            # the gap looks like "[N500N:]"
            # it's weird to have a colon with no description after it
            raise PathParsingError(f'Empty gap name: "{gaptext}"')
    else:
        # Gap looks like "[N500N]"; slice to just "[N500N"
        lengthpartendpos = gaptext.index("]")

    if gaptext[lengthpartendpos - 1] == "N":
        if lengthpartendpos - 1 > GAP_PREFIX_LEN:
            gaplen = ui_utils.get_num(
                gaptext[GAP_PREFIX_LEN : lengthpartendpos - 1],
                "Verkko path gap size",
            )
            return Gap(length=gaplen, gaptype=gaptype)
        else:
            raise PathParsingError(f'Empty gap length: "{gaptext}"')
    else:
        raise PathParsingError(f'Gap length does not end with N: "{gaptext}"')


def get_paths_from_verkko_tsv(tsv_fp, orientation_in_name=True):
    """Loads paths from a Verkko-style TSV file.

    Parameters
    ----------
    tsv_fp: str
        A path to a TSV file.

    orientation_in_name: bool
        Same interpretation as with get_paths_from_agp(). True means that node
        or edge names include orientations if negative (e.g. -5 vs. 5); False
        means that this is not the case.

    Returns
    -------
    paths: defaultdict of str -> list of str or Gap
        Maps path names to a list of sequence (node or edge) names in the path.
        Gaps are represented as Gap objects in the list.

    Raises
    ------
    PathParsingError or UIError
        If the file looks invalid.

    Notes
    -----
    In practice, as of writing this should only be used with nodes in Verkko
    GFA files (where we know that orientation_in_name=True). But I guess we
    might as well support checking if orientation_in_name=False, so that
    this kind of file can be used with other graphs if desired (it seems easier
    to create than AGP files).

    References
    ----------
    https://github.com/marbl/verkko
    """
    paths = get_paths_dict_from_tsv(tsv_fp, "path")
    outpaths = {}
    for name, ids in paths.items():
        path_things = []
        path_has_nongaps = False
        for i in ids:
            if i.startswith(config.VERKKO_PATH_GAP_PREFIX):
                path_things.append(parse_verkko_tsv_gap(i))
            else:
                path_things.append(
                    parse_verkko_tsv_seqname(
                        i, orientation_in_name=orientation_in_name
                    )
                )
                path_has_nongaps = True
        if len(path_things) == 0:
            # this case seems impossible to trigger, since even an
            # empty paths column will result in [""] due to how
            # .split(",") works in get_paths_dict_from_tsv(). (And
            # that will cause parse_verkko_tsv_seqname() to raise
            # an error.) Anyway i guess we can keep this check here
            # out of paranoia
            raise PathParsingError(f'Empty path: {name} -> "{ids}"')
        if not path_has_nongaps:
            raise PathParsingError(f"Path {name} only has gaps???")
        outpaths[name] = path_things
    return outpaths


def get_paths_from_flye_info(fp):
    """Loads information about contig/scaffold paths from Flye output.

    This assumes that the graph being provided as input is a DOT file from
    Flye. If the user specifies this kind of file for a GFA file from Flye,
    then there is different logic elsewhere that parses the contig metadata
    / etc. and associates _that_ with the nodes in the graph.

    Parameters
    ----------
    fp: str
        A path to the assembly_info.txt file.

    Returns
    -------
    paths: defaultdict of str -> list of str or Gap
        Maps path names to a list of edge IDs / Gaps in the path.
        This ignores * entries on the path (indicating "terminal graph node"s
        per the Flye documentation).

    Raises
    ------
    PathParsingError
        If the file looks invalid.

    References
    ----------
    https://github.com/mikolmogorov/Flye/blob/flye/docs/USAGE.md
    """
    paths = get_paths_dict_from_tsv(fp, "graph_path")
    trimmedpaths = {}
    for name, edgeids in paths.items():
        path_edge_ids = []
        path_has_nongaps = False
        for i in edgeids:
            if i == "*":
                continue
            elif i == "??":
                path_edge_ids.append(Gap())
            else:
                path_edge_ids.append(i)
                path_has_nongaps = True
        if len(path_edge_ids) == 0:
            # maybe the path only has *s or something...?
            raise PathParsingError(f'Invalid path: {name} -> "{edgeids}"')
        if not path_has_nongaps:
            raise PathParsingError(f"Path {name} only has gaps???")
        trimmedpaths[name] = path_edge_ids
    return trimmedpaths


def get_path_maps(id2obj, paths, nodes=True):
    """Creates mappings between component size ranks and path names.

    Parameters
    ----------
    id2obj: dict of str -> (Node or Edge)
        Maps node or edge IDs to Node / Edge objects in the graph. This should
        only contain nodes (if nodes=True) or edges (if edges=True).

    paths: dict of str -> list of str or Gap
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
            if type(name) is not Gap:
                objname2pathnames[name].add(pathname)
    pathname2ccnum = {}

    for obj in id2obj.values():
        if nodes:
            objname = obj.basename
        else:
            # An edge-centric graph might have fake edges! Ignore them,
            # of course, since they should not be "part of" any path. (I mean
            # you could make a tortured argument for a path that passes
            # through stuff adjacent to fake edges but WHATEVER that's not
            # important for now)
            if not obj.is_fake:
                # NOTE: this will fail if there exists a (real) edge in the
                # graph that does not have a user-specified ID. this is by
                # design, since such a graph is invalid. if we realllly wanna
                # allow real edges to not have user-specified IDs in these
                # kinds of graphs then we should modify the parser and also
                # just make this call has_userspecified_id() first to check
                objname = obj.get_userspecified_id()

        # Is this node or edge present in at least one of the input paths?
        if objname in objname2pathnames:
            # Yes, it is. Go through all paths it is contained in.
            for pathname in objname2pathnames[objname]:
                # Have we already seen this path?
                if pathname in pathname2ccnum:
                    # Have we recorded this path as being in a *different* cc?
                    if pathname2ccnum[pathname] != obj.cc_num:
                        # TODO: adjust to allow for multi-cc paths for verkko
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
            if type(objname) is not Gap:
                objname2pathnames[objname].add(pathname)

    return ccnum2pathnames, objname2pathnames, pathname2ccnum


def get_available_count_badge_text(num_available, total_num):
    return f"{num_available:,} / {total_num:,}"


def merge_paths(curr_paths, new_paths):
    """Merges paths in new_paths into curr_paths.

    Parameters
    ----------
    curr_paths: dict of str -> list of str or Gap
    new_paths: dict of str -> list of str or Gap

    Returns
    -------
    None
        (This will update curr_paths in place.)

    Raises
    ------
    PathParsingError
        If any path names (i.e. dict keys) are shared between curr_paths and
        new_paths. We don't want to risk data loss, so we complain loudly
        if the user provided multiple sources of paths that use the same IDs.
    """
    i0 = set(curr_paths.keys())
    i1 = set(new_paths.keys())
    if i0 & i1:
        raise PathParsingError("Duplicate paths found between sources?")
    curr_paths.update(new_paths)
