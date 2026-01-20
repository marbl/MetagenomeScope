import re
import time
import statistics
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from collections import defaultdict
from dash import html
from . import css_config, ui_config, config, name_utils
from .errors import UIError, WeirdError
from .gap import Gap


def pluralize(num, thing="edge"):
    """Pluralizes an integer number of things.

    Parameters
    ----------
    num: int
        Number of things.

    thing: str
        Singular name of the thing.

    Returns
    -------
    str
        If num == 1, then this will be "1 [thing]."
        Otherwise, this will be "[num] [things]."

    Notes
    -----
    Yeah, if you have a thing that has a weird irregular plural (e.g. "beef",
    lol -- https://www.rd.com/list/irregular-plurals/) then this will produce
    something that looks grammatically wonky.

    References
    ----------
    yanked from metaLJA's codebase (... i wrote this)
    """
    if num == 1:
        return f"1 {thing}"
    return f"{num:,} {thing}s"


def get_approx_length_disclaimer_if_needed(ag):
    if ag.lengths_are_approx:
        return html.P(
            'Note that lengths were only stored approximately (e.g. "5k" '
            "instead of 5,423) in the input graph file."
        )
    return None


def fmt_qty(quantity, unit="bp", na="N/A"):
    if quantity is not None:
        return f"{quantity:,} {unit}"
    else:
        return na


def get_length_info(ag):
    return html.Table(
        html.Tbody(
            [
                html.Tr(
                    [
                        html.Th(f"Total {ag.seq_noun} sequence length"),
                        html.Th(f"N50 of {ag.seq_noun} sequence lengths"),
                    ]
                ),
                html.Tr(
                    [
                        html.Td(fmt_qty(ag.total_seq_len, ag.length_units)),
                        html.Td(fmt_qty(ag.n50, ag.length_units)),
                    ]
                ),
            ]
        ),
        className=css_config.INFO_DIALOG_TABLE_CLASSES,
    )


def close_to_int(f, epsilon=config.EPSILON):
    return abs(f - round(f)) < epsilon


def round_to_int_if_close(f, epsilon=config.EPSILON):
    if close_to_int(f, epsilon):
        return round(f)
    else:
        return f


def fmt_cov(cov):
    if type(cov) is int or close_to_int(cov):
        return f"{round(cov):,}x"
    else:
        return f"{cov:,.2f}x"


def get_cov_info(ag):
    if not ag.has_covs:
        return [None]
    covhtml = html.Span(
        ui_config.COVATTR2SINGLE[ag.cov_field], className="fw-bold"
    )
    srcnoun = f"{ag.cov_source}s"
    have = "have"
    if ag.missing_cov_ct == 0:
        if len(ag.covs) == 1:
            # "the graph's only (?) edge has ..."
            defct = "the graph's only (?)"
            srcnoun = ag.cov_source
            have = "has"
        else:
            # "all edges have ..."
            defct = f"all {len(ag.covs):,}"
    else:
        # "x / y edges have ..."
        defct = f"{len(ag.covs):,} / {len(ag.covs) + ag.missing_cov_ct:,} "
        if len(ag.covs) == 1:
            # "1 / y edge has ..."
            srcnoun = ag.cov_source
            have = "has"
    introtext = html.P(
        [
            "Additionally, ",
            html.Span(f"{defct} {srcnoun}", className="fw-bold"),
            f" {have} a defined ",
            covhtml,
            ".",
        ]
    )
    tbl = html.Table(
        html.Tbody(
            [
                html.Tr(
                    [
                        html.Th(["Min ", covhtml]),
                        html.Th(["Median ", covhtml]),
                        html.Th(["Average ", covhtml]),
                        html.Th(["Max ", covhtml]),
                    ]
                ),
                html.Tr(
                    [
                        html.Td(fmt_cov(min(ag.covs))),
                        html.Td(fmt_cov(statistics.median(ag.covs))),
                        html.Td(fmt_cov(statistics.mean(ag.covs))),
                        html.Td(fmt_cov(max(ag.covs))),
                    ]
                ),
            ]
        ),
        className=css_config.INFO_DIALOG_TABLE_CLASSES,
    )
    return [introtext, tbl]


def add_error_toast(
    toasts,
    title_text="Error",
    body_text=None,
    body_html=None,
    header_color="#990000",
):
    return add_toast(
        toasts,
        title_text=title_text,
        body_text=body_text,
        body_html=body_html,
        icon="bi-exclamation-octagon",
        header_color=header_color,
    )


def add_warning_toast(
    toasts,
    title_text="Warning",
    body_text=None,
    body_html=None,
    header_color="#d1872c",
):
    return add_toast(
        toasts,
        title_text=title_text,
        body_text=body_text,
        body_html=body_html,
        icon="bi-exclamation-triangle",
        header_color=header_color,
    )


def add_path_toast(
    toasts,
    path_name,
    path_contents,
    nodes=True,
    header_color=css_config.BADGE_AVAILABLE_COLOR,
):
    """Adds a fancy toast message showing the contents of a path."""
    # path_contents is a list of node/edge names, with optional Gap objs
    nongap_ct = 0
    gap_ct = 0
    path_p_children = []
    after_first = False
    for e in path_contents:
        if after_first:
            path_p_children.append(", ")
        if type(e) is Gap:
            gap_ct += 1
            path_p_children.append(html.Span(str(e), className="fw-bold"))
        else:
            nongap_ct += 1
            path_p_children.append(str(e))
        after_first = True

    ngnoun = "node" if nodes else "edge"
    ngct = pluralize(nongap_ct, ngnoun)
    gct = pluralize(gap_ct, "gap")
    body_html = html.Div(
        [
            html.P(
                f"{ngct}, {gct}.",
                className="fw-bold",
                style={"text-align": "center"},
            ),
            html.P(
                path_p_children,
                className="font-monospace",
                style={"margin-bottom": 0},
            ),
        ],
        className="toast-body",
    )
    return add_toast(
        toasts,
        title_text=path_name,
        body_html=body_html,
        icon="bi-list-nested",
        header_color=header_color,
        extra_title_classes="font-monospace",
    )


def add_toast(
    toasts,
    title_text="Error",
    body_text=None,
    body_html=None,
    icon="bi-exclamation-lg",
    header_color=None,
    extra_title_classes="",
):
    if toasts is None:
        toasts = []
    new_toast = create_toast(
        title_text=title_text,
        body_text=body_text,
        body_html=body_html,
        icon=icon,
        header_color=header_color,
        extra_title_classes=extra_title_classes,
    )
    # adding the new toast BEFORE the other toasts does put it on top if any
    # others are still on the screen, but it causes weird behavior if any
    # other toasts have been hidden (probably due to bootstrap css/js details).
    # easier to just put the newest toast at the bottom. probably there will
    # only be like 1-2 of these visible at a time for most users anyway
    return toasts + [new_toast]


def get_toast_timestamp():
    t = time.strftime("%I:%M:%S %p").lower()
    # trim off leading "0" for the hour (e.g. "05:40:10 pm" -> "5:40:10 pm")
    # this isnt really standard practice or anything i just think it looks nice
    if t[0] == "0":
        t = t[1:]
    return t


def create_toast(
    title_text="Error",
    body_text=None,
    body_html=None,
    icon="bi-exclamation-lg",
    header_color=None,
    extra_title_classes="",
):
    # https://getbootstrap.com/docs/5.3/components/toasts/#live-example
    # For a list of possible icons, see https://icons.getbootstrap.com/
    header_style = {}
    if header_color is not None:
        header_style = {"color": header_color}
    toast = html.Div(
        [
            # toast header
            html.Div(
                [
                    html.I(className=f"bi {icon}", style=header_style),
                    html.Span(
                        title_text,
                        className=f"iconlbl me-auto toast-title {extra_title_classes}",
                        style=header_style,
                    ),
                    html.Small(get_toast_timestamp()),
                    html.Button(
                        className="btn-close",
                        type="button",
                        **{
                            "data-bs-dismiss": "toast",
                            "aria-label": "Close",
                        },
                    ),
                ],
                className="toast-header",
            ),
        ],
        # Hide toasts by default. We will use Bootstrap through JS to
        # show them later. See the client-side callback in the main app code.
        className="toast",
        role="alert",
        **{
            "aria-live": "assertive",
            "aria-atomic": "true",
            # Custom data attribute used to ensure that we only show each
            # toast message once. Apparently making up HTML attributes is ok,
            # per https://stackoverflow.com/a/432201
            "data-mgsc-shown": "false",
        },
    )
    if body_text is not None:
        if body_html is not None:
            raise WeirdError("body_text and body_html are mutually exclusive")
        else:
            toast.children.append(html.Div(body_text, className="toast-body"))
    else:
        if body_html is not None:
            toast.children.append(body_html)

    return toast


def decr_size_rank(size_rank, minval, maxval):
    if size_rank <= minval:
        return minval
    elif size_rank > maxval:
        return maxval
    else:
        return size_rank - 1


def incr_size_rank(size_rank, minval, maxval):
    if size_rank < minval:
        return minval
    elif size_rank >= maxval:
        return maxval
    else:
        return size_rank + 1


def get_distance(dist):
    if len(dist) == 0:
        raise UIError("No distance specified.")
    try:
        d = int(dist)
    except ValueError:
        raise UIError(f"{dist} is not a valid integer.")
    if d < 0:
        raise UIError("Distance must be at least 0.")
    return d


def get_maxx(maxx):
    if maxx is None or len(maxx) == 0:
        return None
    try:
        m = float(maxx)
    except ValueError:
        raise UIError(f"{maxx} is not a valid number.")
    if m < 0:
        raise UIError("Maximum x value must be at least 0.")
    return round_to_int_if_close(m)


def truncate_hist(xvals, title, maxx):
    if maxx is None:
        return xvals, title
    else:
        return [
            x for x in xvals if x <= maxx
        ], title + f", truncated to x \u2264 {maxx:,}"


def get_hist_nbins(nbins):
    # Allow "" and None (None should be the default since there is nothing
    # in the "value" attr of the input)
    # And, 0 is the default - it means don't impose an upper bound # of bins
    # as far as I can tell.
    #
    # If the user specifies SOMETHING but it's not a valid int, then we
    # show a toast and don't bother updating the hist
    ibins = 0
    if nbins is not None and len(nbins) > 0:
        try:
            ibins = int(nbins)
        except ValueError:
            raise UIError(f"{nbins} is not a valid integer.")
        if ibins < 0:
            raise UIError("Number of bins must be at least 0.")
    return ibins


def say_goodrange(maxcc, both=False):
    if maxcc > 1:
        if both:
            out = "Both must"
        else:
            out = "Must"
        return out + f" be in the range 1 \u2013 {maxcc}."
    else:
        # should never happen, since the UI should hide the
        # cc selector in this case
        return "The graph only has 1 component. How did you even get here?"


def say_gibberish_msg(maxcc, for_single_entry=True):
    # show useful examples of ranges. If there are just 2 components, though,
    # then show more boring ranges.
    # Note that we should never get here if maxcc == 1. (Um, if we do, though,
    # it's not the end of the world. The user will just see an error message
    # that includes "1 - 2". It will be okay.)
    if maxcc > 2:
        examplerange = f"2 - {maxcc}"
        examplehrange = "2 -"
    else:
        examplerange = "1 - 2"
        examplehrange = "1 -"
    suffix = (
        "be either a single number "
        '(e.g. "1"), a range of numbers (e.g. '
        f'"{examplerange}"), or a half-open range of '
        f'numbers (e.g. "{examplehrange}").'
    )
    if for_single_entry:
        return "Must " + suffix
    else:
        return "No component size rank(s) specified. Each entry must " + suffix


def get_sr_errmsg(e, for_range, explanation):
    out = "Invalid component size rank"
    if type(for_range) is bool:
        if for_range:
            out += " range"
    else:
        if len(for_range) == 2:
            out += f's "{for_range[0]}" and "{for_range[1]}" in the range'
        else:
            out += f' "{for_range[0]}" in the range'
    return out + f' "{e}" specified. {explanation}'


def get_single_sr_num_if_valid(
    text, maxcc, default_if_empty, fail_if_out_of_range=False
):
    if len(text) == 0:
        # support half-open ranges
        return default_if_empty
    if re.match("^#?[0-9]+$", text):
        if text[0] == "#":
            text = text[1:]
        i = int(text)
        if i >= 1 and i <= maxcc:
            return i
        elif fail_if_out_of_range:
            raise UIError(get_sr_errmsg(text, False, say_goodrange(maxcc)))
    return None


def get_size_ranks(val, maxcc):
    """Returns a set of component size ranks based on user input.

    Parameters
    ----------
    val: str
        Text input by the user. This should be a a comma-separated
        list of component size ranks to draw: each entry can be something
        like "3" (draw cc #3), "3-5" (draw ccs 3-5), "-3" (draw ccs 1-3),
        or "3-" (draw all ccs with size ranks >= 3).

    maxcc: int
        The number of components in the graph. Or, equivalently, the largest
        "valid" component size rank is maxcc.

    Returns
    -------
    set of int
        Selected component size ranks.

    Raises
    ------
    UIError
        If the input text is malformed in some way. There are a lot of ways
        for this to go wrong.

    Notes
    -----
    I tested this function pretty thoroughly; you may want to see those tests
    for some examples of how this works. (Like, I COULD document every possible
    thing this function accounts for here, but that would probably become out-
    of-date like immediately so it doesn't seem very useful. Hopefully this
    code isn't that hard to read...)
    """
    if val is None or len(val.strip()) == 0:
        raise UIError(say_gibberish_msg(maxcc, for_single_entry=False))
    srs = set()
    entries = val.split(",")
    # Each entry e in "entries" can be one of:
    # * a single size rank (e.g. "2")
    # * a range of size ranks (e.g. "2-5")
    # * a half-open range of size ranks (e.g. "-5", "8-")
    #   indicating that we should select all size ranks <= or >= some value
    for e in entries:
        e = e.strip()
        i = get_single_sr_num_if_valid(e, maxcc, "", fail_if_out_of_range=True)
        if type(i) is int:
            # e is a single size rank
            srs.add(i)
        elif i == "":
            # if the user accidentally includes an empty entry (e.g.
            # they typed "1,2,3,,4") then just be polite and ignore this.
            # later we'll check to make sure that we catch diabolical cases
            # like ",,,,"
            continue
        else:
            # e is a range? hopefully???
            r0 = None
            r1 = None
            for d in ui_config.RANGE_DASHES:
                ct = e.count(d)
                if ct == 1:
                    if r0 is not None:
                        raise UIError(
                            get_sr_errmsg(
                                e, True, "Multiple dash characters present?"
                            )
                        )
                    parts = e.split(d)
                    r0 = parts[0].strip()
                    r1 = parts[1].strip()
                    if len(r0) == 0 and len(r1) == 0:
                        # this case catches the silly situation where e is
                        # just a "-" or something. we COULD take this to mean
                        # "select all components" but i doubt that is a good
                        # idea (i expect most times people hit this it will be
                        # in error)
                        raise UIError(
                            get_sr_errmsg(
                                e,
                                True,
                                (
                                    "Please give a start and/or an end for the "
                                    "range."
                                ),
                            )
                        )
                elif ct > 1:
                    raise UIError(
                        get_sr_errmsg(
                            e, True, f'The "{d}" occurs multiple times?'
                        )
                    )

            # If none of the acceptable dash characters were present in e,
            # we will end up here -- with r0 and r1 both set to None.
            if r0 is None:
                # The error message we use at this point shows an example
                # range "1 - maxcc". If maxcc == 1, this will not make
                # sense to the user. Um... we should never get here if
                # maxcc == 1 because the cc size rank selection UI should
                # be hidden, but just in case I GUESS we can handle this ok.
                if maxcc == 1:
                    raise UIError(
                        get_sr_errmsg(
                            e,
                            False,
                            (
                                "Literally it can only be 1. How did you get "
                                "here lol"
                            ),
                        )
                    )
                else:
                    raise UIError(
                        get_sr_errmsg(
                            e,
                            False,
                            say_gibberish_msg(maxcc),
                        )
                    )
            # The defaults for half-open ranges are 1 (for i0) and maxcc
            # (for i1). So, for example: "-5" represents [1, 2, 3, 4, 5],
            # and "5-" represents [5, 6, 7, 8, ... maxcc].
            #
            # Thankfully we don't have to worry about the case where both r0
            # and r1 are empty (causing us to draw all ccs), because we have
            # already checked above for this specific case.
            i0 = get_single_sr_num_if_valid(r0, maxcc, 1)
            i1 = get_single_sr_num_if_valid(r1, maxcc, maxcc)
            if i0 is None:
                if i1 is None:
                    raise UIError(
                        get_sr_errmsg(
                            e, (r0, r1), say_goodrange(maxcc, both=True)
                        )
                    )
                raise UIError(get_sr_errmsg(e, (r0,), say_goodrange(maxcc)))
            elif i1 is None:
                raise UIError(get_sr_errmsg(e, (r1,), say_goodrange(maxcc)))

            # I GUESS we can allow useless ranges of the form n-n, which
            # means "draw all components from n to n", aka "just draw
            # component n". idk probs doesn't matter. allowing this has the
            # nice? side effect of making silly half-open ranges like "-1"
            # and "C-" (where C = the largest size rank in a graph) work.
            if i1 < i0:
                raise UIError(
                    get_sr_errmsg(
                        e, True, "The end should be bigger than the start."
                    )
                )
            # add all cc nums in the inclusive interval [i0, i1] to
            # srs. you could make a reasonable point here about how it
            # would be more efficient to just store the range start-/end-
            # points... hmm, maybe we could switch to that eventually,
            # i guess that would actually be doable
            srs.update(range(i0, i1 + 1))

    # catch cases where the input was something like ",,,,"
    if len(srs) == 0:
        raise UIError(say_gibberish_msg(maxcc, for_single_entry=False))

    return srs


def _get_from_text(a, b, prefix="#"):
    return f"{prefix}{a:,} \u2013 {b:,}"


def _get_range_text(r):
    # We assume r is a continuous range of integers. It can contain a single
    # element.
    if len(r) == 1:
        return f"#{r[0]:,}"
    else:
        return _get_from_text(r[0], r[-1])


def _get_range_text_from_bounds_only(low, high):
    # if we wanna be super anxious about performance and avoid writing out
    # range(1, |components|) when the user draws all ccs
    if low == high:
        return f"#{low:,}"
    else:
        return _get_from_text(low, high)


def fmt_num_ranges(nums):
    if len(nums) == 1:
        return f"#{nums[0]:,}"
    nums = sorted(nums)
    i = 0
    curr_range = []
    range_texts = []
    while i < len(nums):
        if len(curr_range) == 0 or curr_range[-1] + 1 == nums[i]:
            curr_range.append(nums[i])
        else:
            range_texts.append(_get_range_text(curr_range))
            curr_range = [nums[i]]
        i += 1
    range_texts.append(_get_range_text(curr_range))
    return "; ".join(range_texts)


def get_curr_drawn_text(done_flushing, ag):
    draw_type = done_flushing["draw_type"]

    if draw_type == config.DRAW_ALL:
        t = _get_range_text_from_bounds_only(1, len(ag.components))

    elif draw_type == config.DRAW_CCS:
        t = fmt_num_ranges(done_flushing["cc_nums"])

    elif draw_type == config.DRAW_AROUND:
        d = done_flushing["around_dist"]
        node_ids = done_flushing["around_node_ids"]
        node_names = name_utils.condense_splits(
            ag.get_node_names_from_ids(node_ids)
        )
        noun = "node" if len(node_names) == 1 else "nodes"
        t = f'around {noun} {", ".join(sorted(node_names))} (distance {d:,})'

    else:
        raise WeirdError(f"Unrecognized draw type: {draw_type}")
    return t


def get_node_names(val):
    """Returns a set of node names based on user input.

    This is kind of analogous to get_size_ranks() above -- the same idea, of
    converting arbitrary comma-separated user inputs to a collection of IDs.

    Parameters
    ----------
    val: str
        Text input by the user. This should be a comma-separated list of node
        names (just a single node name is fine also).

    Returns
    -------
    set of str
        Node names described by the input.

    Raises
    ------
    UIError
        If the input text is malformed in some way. Currently, this can only
        be triggered here by there being no node names in the input text.

    Notes
    -----
    - This does not actually check if any of these nodes are in the graph. This
      is done by the caller, e.g. in AssemblyGraph.get_nodename2ccnum().

    - This assumes that node names do not contain whitespace (technically I
      think this allows node names to contain inner whitespace, but they can't
      start or end with whitespace). Look, if your names have whitespace then
      something is very wrong; we should be rejecting such graphs up front
      anyway.
    """
    nothing_err = UIError("No node name(s) specified.")
    if val is None or len(val.strip()) == 0:
        raise nothing_err

    node_names = set(n.strip() for n in val.split(","))

    # Ignore ""s resulting from inputs like "node1,,node2"
    node_names.discard("")

    # catch the evil ",,," case
    if len(node_names) == 0:
        raise nothing_err

    return node_names


def get_fancy_node_name_list(node_names, quote=True):
    # sorting the node names makes these error messages easier to read for the
    # user, i think. it also makes testing easier
    if quote:
        sn = [f'"{n}"' for n in sorted(node_names)]
    else:
        sn = sorted(node_names)
    return ", ".join(sn)


def fail_if_unfound_nodes(unfound_nodes):
    if len(unfound_nodes) == 1:
        n = unfound_nodes.pop()
        raise UIError(f'Can\'t find a node with name "{n}" in the graph.')

    elif len(unfound_nodes) > 1:
        ns = get_fancy_node_name_list(unfound_nodes)
        raise UIError(f"Can't find nodes with names {ns} in the graph.")


def get_single_node_in_other_cc_summary(undrawn_nodes, ag):
    n = undrawn_nodes[0]
    c = ag.nodename2objs[n][0].cc_num
    return html.Div(
        f'Node "{n}" is not currently drawn. It\'s in component #{c:,}.',
        className="toast-body",
    )


def summarize_undrawn_nodes(undrawn_nodes, ag, all_undrawn):
    """Produces a HTML summary of undrawn nodes, to be shown after searching.

    This is used when creating a toast message indicating an error or warning
    arising from searching from nodes that are not currently drawn.
    """
    if len(undrawn_nodes) == 1:
        return get_single_node_in_other_cc_summary(undrawn_nodes, ag)
    else:
        # If the user searched for the basename of a split node, then both of
        # this node's splits will be in undrawn_nodes. To simplify the output,
        # "condense" these split nodes together here.
        undrawn_nodes = name_utils.condense_splits(undrawn_nodes)

        # If the only thing that the user searched for was the two splits of a
        # node (for some reason???), go back and use the same message as above
        if len(undrawn_nodes) == 1:
            return get_single_node_in_other_cc_summary(undrawn_nodes, ag)

        # okay if we've made it here then legitimately there are at least two
        # nodes that are not currently drawn
        if all_undrawn:
            s1 = "None of these nodes are currently drawn."
        else:
            # it would be possible to show a fraction (e.g. "2 / 5 nodes")
            # based on what nodes *are* drawn, but that requires accounting
            # for split nodes, duplicates, etc. and is messy.
            s1 = f"{len(undrawn_nodes):,} nodes are not currently drawn."

        undrawn_cc_to_nodes = defaultdict(list)
        for n in undrawn_nodes:
            # If we condensed split nodes together (e.g. "40-L" and "40-R"
            # were merged into "40"), then the resulting node names may not
            # be in the graph at all. But this is okay! ag.nodename2objs maps
            # node basenames to their corresponding split nodes, so we can
            # still look up the basename here without trouble.
            cc_num = ag.nodename2objs[n][0].cc_num
            undrawn_cc_to_nodes[cc_num].append(n)

        if len(undrawn_cc_to_nodes) == 1:
            s2 = "They are all in another component:"
        else:
            s2 = "They are in the following components:"
        intro = html.Div(f"{s1} {s2}")

        theader = [
            html.Thead(
                html.Tr(
                    [html.Th("CC #", className="nowrap"), html.Th("Nodes")]
                )
            )
        ]
        rows = []
        for c in sorted(undrawn_cc_to_nodes):
            node_list = get_fancy_node_name_list(
                undrawn_cc_to_nodes[c], quote=False
            )
            rows.append(html.Tr([html.Td(f"{c:,}"), html.Td(node_list)]))
        tbody = [html.Tbody(rows)]
        table = dbc.Table(theader + tbody)
        return html.Div([intro, table], className="toast-body")


def get_screenshot_basename():
    # this should be ISO 8601 compliant. See https://xkcd.com/1179, lol.
    # I am sure there are better ways to represent this tho... if whoever is
    # reading this has strong opinions feel free to open a github issue
    return time.strftime("mgsc-%Y%m%dT%H%M%S")


def get_selected_ele_html(eleType, columnDefs, extra_attrs=[]):
    for a in extra_attrs:
        # Do we know in advance a human-readable name and a good type for
        # this field? If so, get this info from ui_config.
        if eleType == "Node":
            if a in ui_config.NODEATTRS_SKIP:
                continue
            attrRef = ui_config.NODEATTR2HRT
        elif eleType == "Edge":
            if a in ui_config.EDGEATTRS_SKIP:
                continue
            attrRef = ui_config.EDGEATTR2HRT
        else:
            # patterns shouldn't have extra attrs, as of writing, so we
            # shouldn't end up here. but let's be defensive.
            attrRef = {}
        if a in attrRef:
            headerName, colType = attrRef[a]
        else:
            # Okay, we don't already know about this field. That's fine; just
            # show the field name to the user directly and treat it as text
            headerName = a
            colType = "text"

        col = {
            "field": a,
            "headerName": headerName,
            "cellDataType": colType,
            "cellClass": "fancytable-cells",
            "headerClass": "fancytable-header-extra",
        }

        if eleType == "Node":
            if a in ui_config.NODEATTR2FMT:
                col["valueFormatter"] = ui_config.NODEATTR2FMT[a]
        elif eleType == "Edge":
            if a in ui_config.EDGEATTR2FMT:
                col["valueFormatter"] = ui_config.EDGEATTR2FMT[a]

        columnDefs.append(col)
    return [
        html.Div(
            [
                f"{eleType}s",
                dbc.Badge(
                    "0",
                    pill=True,
                    className=css_config.BADGE_CLASSES,
                    color=css_config.BADGE_ZERO_COLOR,
                    id=f"selected{eleType}Count",
                ),
                html.Span(
                    html.I(
                        className="bi bi-caret-right-fill",
                        id=f"selected{eleType}Opener",
                    ),
                    className="opener",
                ),
            ],
            className="eleTableHeader",
            id=f"selected{eleType}Header",
        ),
        dag.AgGrid(
            rowData=[],
            columnDefs=columnDefs,
            columnSize="responsiveSizeToFit",
            className=css_config.SELECTED_ELE_TBL_CLASSES + " removedEntirely",
            id=f"selected{eleType}List",
            dashGridOptions={
                "overlayNoRowsTemplate": f"No {eleType.lower()}s selected.",
                # We need to include this, or column names that include periods
                # (e.g. "mult." in Flye output) will completely explode the
                # tables and make me spend like an hour debugging it.
                # https://stackoverflow.com/q/58772051
                # https://dash.plotly.com/dash-ag-grid/column-definitions#suppressing-field-dot-notation
                "suppressFieldDotNotation": True,
            },
            dangerously_allow_code=True,
        ),
    ]


def get_badge_color(ct, selection_only=True):
    """Decides the color of a badge showing a count of some elements.

    Parameters
    ----------
    ct: int
        The number of elements (nodes, edges, patterns, or paths) to show.

    selection_only: bool
        If ct > 0, the color returned will vary depending on this flag.
        selection_only = True means that this is a count of *selected*
        elements (e.g. selected nodes). selection_only = False means that
        this is a count of *available* elements (e.g. paths that are relevant
        to the currently drawn region of the graph).

    References
    ----------
    See https://www.dash-bootstrap-components.com/docs/components/badge/
    """
    if ct == 0:
        return css_config.BADGE_ZERO_COLOR
    elif selection_only:
        return css_config.BADGE_SELECTED_COLOR
    else:
        return css_config.BADGE_AVAILABLE_COLOR


def show_patterns(draw_settings):
    return ui_config.SHOW_PATTERNS in draw_settings


def do_recursive_layout(draw_settings):
    return ui_config.DO_RECURSIVE_LAYOUT in draw_settings


def use_gv_ports(draw_settings):
    return ui_config.USE_GV_PORTS in draw_settings
