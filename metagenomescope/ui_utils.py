import re
import time
import copy
import statistics
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from collections import defaultdict
from dash import html, dcc
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


def get_patt_info(ag):
    pct = len(ag.pattid2obj)
    introtext = html.P(
        [
            "We identified ",
            html.Span(pluralize(pct, "pattern"), className="fw-bold"),
            " in the graph:",
        ]
    )
    tbl = html.Table(
        html.Tbody(
            [
                html.Tr(
                    [
                        html.Th(
                            "# bubbles",
                            style={
                                "background-color": config.PT2COLOR[
                                    config.PT_BUBBLE
                                ]
                            },
                        ),
                        html.Th(
                            "# frayed ropes",
                            style={
                                "background-color": config.PT2COLOR[
                                    config.PT_FRAYEDROPE
                                ]
                            },
                        ),
                        html.Th(
                            "# chains",
                            style={
                                "background-color": config.PT2COLOR[
                                    config.PT_CHAIN
                                ]
                            },
                        ),
                        html.Th(
                            "# cyclic chains",
                            style={
                                "background-color": config.PT2COLOR[
                                    config.PT_CYCLICCHAIN
                                ]
                            },
                        ),
                        html.Th(
                            "# bipartites",
                            style={
                                "background-color": config.PT2COLOR[
                                    config.PT_BIPARTITE
                                ]
                            },
                        ),
                    ]
                ),
                html.Tr(
                    [
                        html.Td(f"{len(ag.bubbles):,}"),
                        html.Td(f"{len(ag.frayed_ropes):,}"),
                        html.Td(f"{len(ag.chains):,}"),
                        html.Td(f"{len(ag.cyclic_chains):,}"),
                        html.Td(f"{len(ag.bipartites):,}"),
                    ]
                ),
            ]
        ),
        className=css_config.INFO_DIALOG_TABLE_CLASSES,
    )
    return [introtext, tbl]


def close_to_int(f, epsilon=config.EPSILON):
    return type(f) is int or abs(f - round(f)) < epsilon


def round_to_int_if_close(f, epsilon=config.EPSILON):
    if close_to_int(f, epsilon):
        return round(f)
    else:
        return f


def fmt_maybe_int(n, suffix="", precision=2, use_thousands_sep=True):
    if use_thousands_sep:
        t = ","
    else:
        t = ""
    if close_to_int(n):
        return f"{round(n):{t}}{suffix}"
    else:
        # turns out you can just specify {precision} to fill in ".2f" with
        # a variable! crazy. https://stackoverflow.com/a/58435117
        return f"{n:{t}.{precision}f}{suffix}"


def fmt_cov(cov):
    # My default inclination is to use 2 digits of precision (e.g. "123.45x")
    # but I think that is probably overkill for things like edge labels
    return fmt_maybe_int(cov, suffix="x", precision=1)


def fmt_approx_length(alen):
    # for turning flye lengths (e.g. "0.6k", stored as 600) back into "0.6k"
    t = round_to_int_if_close(alen / 1000)
    return fmt_maybe_int(t, suffix="k", precision=1)


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
                    html.Small(
                        get_toast_timestamp(), className="toast-timestamp"
                    ),
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


def is_too_big(f, max_val, max_incl):
    if max_incl:
        return f > max_val
    else:
        return f >= max_val


def is_too_small(f, min_val, min_incl):
    if min_incl:
        return f < min_val
    else:
        return f <= min_val


def get_num(
    n,
    name,
    integer=True,
    min_val=0,
    max_val=None,
    min_incl=True,
    max_incl=False,
    none_val=None,
    none_ok=False,
):
    if n is None or (type(n) is str and len(n) == 0):
        if none_ok:
            return none_val
        else:
            raise UIError(f"{name} not specified.")
    if integer:
        func = int
        tname = "integer"
    else:
        func = float
        tname = "number"
    try:
        f = func(n)
    except ValueError:
        raise UIError(f'{name}: "{n}" is not a valid {tname}.')
    # yeah yeah whatever if you select like 99.999999.... and the max is 100
    # and max_incl is False then this can cause problems. whatever that is
    # unimportant imo
    f = round_to_int_if_close(f)
    gt = "\u2265" if min_incl else ">"
    lt = "\u2264" if max_incl else "<"
    err_msg = ""
    bad = False
    check_min = min_val is not None
    check_max = max_val is not None
    if check_min:
        err_msg = f"{name} must be {gt} {min_val:,}"
        bad = is_too_small(f, min_val, min_incl)
        if check_max:
            err_msg += f" and {lt} {max_val:,}"
            bad = bad or is_too_big(f, max_val, max_incl)
    elif check_max:
        err_msg = f"{name} must be {lt} {max_val:,}"
        bad = is_too_big(f, max_val, max_incl)
    if bad:
        raise UIError(err_msg + ".")
    return f


def get_hist_nbins(nbins):
    return get_num(
        nbins,
        "Number of bins",
        min_val=0,
        min_incl=True,
        none_val=0,
        none_ok=True,
    )


def get_maxx(maxx):
    return get_num(
        maxx,
        "Maximum x value",
        integer=False,
        min_val=0,
        min_incl=True,
        none_val=None,
        none_ok=True,
    )


def truncate_hist(xvals, title, maxx):
    if maxx is None:
        return xvals, title
    else:
        return [
            x for x in xvals if x <= maxx
        ], title + f", truncated to x \u2264 {maxx:,}"


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
        Text input by the user. This should be a a comma-/semicolon-separated
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
    entries = val.replace(";", ",").split(",")
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


def _get_fmt_num(n, prefix="#", thousands_seps=True):
    if thousands_seps:
        return f"{prefix}{n:,}"
    else:
        return f"{prefix}{n}"


def _get_from_text(a, b, prefix="#", thousands_seps=True):
    out = _get_fmt_num(a, prefix=prefix, thousands_seps=thousands_seps)
    out += " \u2013 "
    out += _get_fmt_num(b, prefix="", thousands_seps=thousands_seps)
    return out


def _get_range_text(r, thousands_seps=True):
    # We assume r is a continuous range of integers. It can contain a single
    # element.
    if len(r) == 1:
        return _get_fmt_num(r[0], thousands_seps=thousands_seps)
    else:
        return _get_from_text(r[0], r[-1], thousands_seps=thousands_seps)


def _get_range_text_from_bounds_only(low, high):
    # if we wanna be super anxious about performance and avoid writing out
    # range(1, |components|) when the user draws all ccs
    if low == high:
        return f"#{low:,}"
    else:
        return _get_from_text(low, high)


def fmt_num_ranges(nums, thousands_seps=True):
    if len(nums) == 1:
        return _get_fmt_num(nums[0], thousands_seps=thousands_seps)
    nums = sorted(nums)
    i = 0
    curr_range = []
    range_texts = []
    while i < len(nums):
        if len(curr_range) == 0 or curr_range[-1] + 1 == nums[i]:
            curr_range.append(nums[i])
        else:
            range_texts.append(
                _get_range_text(curr_range, thousands_seps=thousands_seps)
            )
            curr_range = [nums[i]]
        i += 1
    range_texts.append(
        _get_range_text(curr_range, thousands_seps=thousands_seps)
    )
    return "; ".join(range_texts)


def get_curr_drawn_text(done_flushing, ag):
    draw_type = done_flushing["draw_type"]

    if draw_type == config.DRAW_ALL:
        t = _get_range_text_from_bounds_only(1, len(ag.components))

    elif draw_type == config.DRAW_CCS:
        if len(done_flushing["orig_cc_nums"]) > 0:
            t = fmt_num_ranges(done_flushing["orig_cc_nums"])
            drawn_cc_ct = len(done_flushing["cc_nums"])
            t += (
                "; filtered to "
                f"{pluralize(drawn_cc_ct, 'nonredundant component')}"
            )
        else:
            t = fmt_num_ranges(done_flushing["cc_nums"])

    elif draw_type == config.DRAW_NR:
        nrccs = list(ag.get_nr_cc_nums())
        nrct = len(nrccs)
        if nrct == 1:
            t = fmt_num_ranges(nrccs)
        else:
            t = _get_range_text_from_bounds_only(1, len(ag.components))
            t += f"; filtered to {pluralize(nrct, 'nonredundant component')}"

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
    converting arbitrary comma-/semicolon-separated user inputs to a collection
    of IDs.

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

    # As with get_size_ranks(), allow semicolons as delimiters
    node_names = set(n.strip() for n in val.replace(";", ",").split(","))

    # Ignore ""s resulting from inputs like "node1,,node2"
    node_names.discard("")

    # catch the evil ",,," case
    if len(node_names) == 0:
        raise nothing_err

    return node_names


def get_fancy_node_name_list(node_names, quote=True, bracket=False):
    # sorting the node names makes these error messages easier to read for the
    # user, i think. it also makes testing easier
    if quote:
        sn = [f'"{n}"' for n in sorted(node_names)]
    else:
        sn = sorted(node_names)
    out = ", ".join(sn)
    if bracket:
        return f"[{out}]"
    else:
        return out


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
            className=css_config.ELE_TBL_CLASSES + " removedEntirely",
            id=f"selected{eleType}List",
            dashGridOptions={
                "overlayNoRowsTemplate": f"No {eleType.lower()}s selected.",
                **ui_config.DASH_GRID_OPTIONS,
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


def get_edge_coloring_options(ag):
    options = [
        {
            "label": ui_config.COLORFUL_RANDOM_TEXT,
            "value": ui_config.COLORING_RANDOM,
        },
        {
            "label": "Uniform",
            "value": ui_config.COLORING_UNIFORM,
        },
    ]
    if "color" in ag.extra_edge_attrs:
        options.append(
            {
                "label": f"{ag.filetype} file",
                "value": ui_config.COLORING_GRAPH,
            }
        )
    return options


def nr_ccs(scope_settings):
    return ui_config.NR_CCS in scope_settings


def show_patterns(scope_settings):
    return ui_config.SHOW_PATTERNS in scope_settings


def do_recursive_layout(modifier_settings):
    return ui_config.DO_RECURSIVE_LAYOUT in modifier_settings


def use_gv_ports(modifier_settings):
    return ui_config.USE_GV_PORTS in modifier_settings


def nrfilter_draw_request(scope_settings, draw_type, cc_nums, ag):
    """Filters a draw request to remove nonredundant components.

    Parameters
    ----------
    scope_settings: list of str
        Corresponds to the scope settings checklist (as of writing, this
        is located in the Layout tab of the drawing options dialog).

    draw_type: str
        Should be one of {DRAW_ALL, DRAW_CCS, DRAW_AROUND} from config.py.
        Indicates what sort of drawing method the user selected.

    cc_nums: set of int
        If draw_type == DRAW_CCS, this should be a set of the corresponding
        component size ranks. Otherwise, this doesn't matter (I think it
        will default to an empty list in practice).

    ag: metagenomescope.graph.AssemblyGraph
        AssemblyGraph object representing the graph that this MetagenomeScope
        instance is visualizing things for.

    Returns
    -------
    draw_type, cc_nums, orig_cc_nums: str, set of int, set of int
        draw_type represents the drawing method we've decided to use for this
        request. Should be one of {DRAW_ALL, DRAW_CCS, DRAW_AROUND, DRAW_NR}.
        This may be different from the input draw_type.

        cc_nums represents the component numbers to *actually* draw. This may
        be a subset of what was requested. If the output draw_type is not
        DRAW_CCS, this will be unchanged from the input.

        If cc_nums ends up being filtered -- and if the output draw_type
        remains as DRAW_CCS -- then orig_cc_nums will be set to what the input
        cc_nums was. This is so that we can display cleaner summaries of what
        the user requested (e.g. "10-100" instead of "10; 12; 14; ...").
        If these conditions are not met, then this will be an empty set.

    Notes
    -----
    It is possible, if the input draw_type is DRAW_CCS, to check if the set
    of filtered component numbers is equal to ag.nr_cc_nums -- and, if so,
    to just switch the output draw_type to DRAW_NR. This could happen if
    e.g. the user requests we draw components "1-" or something like that.

    However! I am not sure I like this, because then the info about what
    is currently drawn can change: e.g. for the E. coli test dataset (61
    components), where ccs 60 and 61 are twins (+278 and -278 respectively),
    requesting ccs "1-60" is identical to requesting "1-61", and so even
    "1-60" will be shown in the currently-drawn text as "1-61; filtered ...".
    Even though the MEANING is the same I don't like changing what the user
    sees if I can help it, right? I dunno.

    (Anyway so TLDR we don't bother doing that particular draw type change even
    though it might save us some storage space in the application.)
    """
    orig_cc_nums = set()
    if nr_ccs(scope_settings):
        # Okay, we know we should filter the draw request to remove NR CCs

        if draw_type == config.DRAW_CCS:
            # draw just the components in the list, but also remove pairs
            # of redundant components. If both a component and its twin
            # are in the list, then draw whichever one of the two is in
            # ag.nr_cc_nums.
            filtered_cc_nums = set()
            for ccn in cc_nums:
                if ccn in ag.nr_cc_nums:
                    filtered_cc_nums.add(ccn)
                else:
                    # Even if ccn is not in ag.nr_cc_nums (i.e. it has a
                    # twin that IS in ag.nr_cc_nums): if its twin is not in
                    # cc_nums (i.e. it was not explicitly requested), then
                    # draw ccn
                    if ag.ccnum2twinccnum[ccn] not in cc_nums:
                        filtered_cc_nums.add(ccn)
                    # if we've made it here, both ccn and its twin were
                    # explicitly requested (i.e. in cc_nums), so ignore ccn
                    # in favor of its twin in ag.nr_cc_nums

            # CASE 1: we are using NR filtering for some set of components.
            if cc_nums != filtered_cc_nums:
                # Some filtering occurred -- meaning that the set of input
                # components is different from the set of components to be
                # drawn. Thus, store the input components for reference.
                orig_cc_nums = cc_nums
            cc_nums = filtered_cc_nums

        elif draw_type == config.DRAW_ALL:
            # CASE 2: we are using NR filtering, and the user requested we draw
            # all components. Use DRAW_NR to indicate that we should just draw
            # all nonredundant components. (Originally this was the only option
            # available for drawing nonredundant stuff, so it is already very
            # fleshed out.)
            #
            # Using a different draw type than DRAW_CCS, lets us show a more
            # concise summary of what is drawn than listing out something like
            # "#1; #3; #5; ..." (and a more accurate summary
            # than saying #1 -- |Components| like we would for DRAW_ALL).
            #
            # (also, no need to set "cc_nums = ag.get_nr_cc_nums()", since
            # the AssemblyGraph will just see DRAW_NR and know to look
            # those up)
            draw_type = config.DRAW_NR

        elif draw_type == config.DRAW_AROUND:
            # CASE 3: we are using NR filtering, but drawing around a set of
            # nodes. NR filtering doesn't impact this.
            pass

        else:
            # CASE 4: the draw type is weird. throw an error.
            raise WeirdError(f'Unrecognized draw type: "{draw_type}"')

    # CASE 5 (if the nr_ccs() check was not True): we are not using NR
    # filtering; don't change the draw type or cc_nums.

    return draw_type, cc_nums, orig_cc_nums


def get_dot_alg_descriptions():
    etal_text = html.Span(
        [html.Span("et al", style={"font-style": "italic"}), ".,"]
    )
    DOT_ALG_DESC = [
        html.P(
            [
                "Hierarchical layout algorithm described in ",
                html.A(
                    [
                        "Gansner ",
                        etal_text,
                        " 1993",
                    ],
                    href="https://doi.org/10.1109/32.221135",
                    # this tells the browser to open this link
                    # in a new tab; we don't wanna move off the
                    # page if the user has already been drawing
                    # stuff
                    target="_blank",
                ),
                ' ("A technique for drawing directed graphs").',
            ]
        ),
    ]
    DOT_ALG_DESC_PATTS = DOT_ALG_DESC + [
        html.P(
            [
                "We'll run ",
                ui_config.DOT_TEXT,
                " recursively: we'll lay out bottom-level ",
                "patterns first, then lay out parent patterns of those "
                "patterns, and eventually lay out the entire graph.",
            ],
            id="dotAlgPatternDesc",
        ),
    ]
    if (
        ui_config.SHOW_PATTERNS in ui_config.DEFAULT_SCOPE_SETTINGS
        and ui_config.DO_RECURSIVE_LAYOUT
        in ui_config.DEFAULT_MODIFIER_SETTINGS
    ):
        dot_alg_desc_used = DOT_ALG_DESC_PATTS
    else:
        dot_alg_desc_used = DOT_ALG_DESC
    return DOT_ALG_DESC, DOT_ALG_DESC_PATTS, dot_alg_desc_used


def get_layout_options_tab(
    node_centric, orientation_in_name, multiple_ccs, default_dot_alg_desc
):

    JS_ALG_WARNING = html.P(
        [
            html.Span("Note:", style={"font-weight": "bold"}),
            " This layout algorithm is run within the web browser. "
            "It may struggle or take a while for large graphs.",
        ]
    )

    DAGRE_ALG_DESC = [
        html.P(
            [
                "Client-side hierarchical layout algorithm (",
                html.A(
                    "GitHub wiki",
                    href="https://github.com/dagrejs/dagre/wiki",
                    target="_blank",
                ),
                ").",
            ]
        ),
        JS_ALG_WARNING,
    ]

    FCOSE_ALG_DESC = [
        html.P(
            [
                "Client-side force-directed layout algorithm described in ",
                html.A(
                    "Balci & Dogrusoz 2021",
                    href="https://doi.org/10.1109/TVCG.2021.3095303",
                    target="_blank",
                ),
                ' ("fCoSE: A fast compound graph layout algorithm with ',
                'constraint support").',
            ]
        ),
        JS_ALG_WARNING,
    ]

    scope_options = copy.deepcopy(ui_config.SCOPE_SETTINGS_OPTIONS)
    default_scope_settings = copy.deepcopy(ui_config.DEFAULT_SCOPE_SETTINGS)
    # Drawing only the nonredundant parts of the graph only makes sense if
    # (1) there are pairs of nodes/edges X and -X in the graph (i.e.
    # ag.orientation_in_name is True) and (2) there are multiple components.
    #
    # If this is NOT the case, then let's just turn off (and disable) the
    # "just show nonredundant ccs" option here. We COULD hide it entirely but
    # I think disabling gives a clearer user experience.
    if not (orientation_in_name and multiple_ccs):
        for o in scope_options:
            if o["value"] == ui_config.NR_CCS:
                o["disabled"] = True
                # tragically there isn't an elegant way to remove an element
                # from a list but not raise an error (at least according to
                # https://old.reddit.com/r/Python/comments/1spcsq) so sure
                # let's just do this the lazy way
                try:
                    default_scope_settings.remove(ui_config.NR_CCS)
                except ValueError:
                    pass
                break

    return html.Div(
        [
            html.Div(
                (
                    "These settings will take "
                    "effect when you redraw the graph."
                ),
                className="drawing-option-topnote",
            ),
            html.H5("What should we draw?"),
            # Eventually we can add other stuff here, e.g. "filter
            # nodes/edges with < X cov"
            #
            # I'm sticking with a standard dcc.Checklist (rather than
            # dbc.Checklist) because I don't like the default formatting
            # of their inline checklists. Even after doing some massaging
            # to make the margins better, there is still an ugly
            # unclickable region between the checkbox and label... maybe I
            # am just doing something wrong, but I think the UX of the
            # dcc.Checklist is better.
            html.Div(
                dcc.Checklist(
                    options=scope_options,
                    value=default_scope_settings,
                    id="scopeSettingsChecklist",
                ),
                className="form-check fancyChecklistInDialog",
            ),
            html.Br(),
            html.H5("How should we draw it?"),
            html.Div(
                dcc.Checklist(
                    options=ui_config.MODIFIER_SETTINGS_OPTIONS,
                    value=ui_config.DEFAULT_MODIFIER_SETTINGS,
                    id="modifierSettingsChecklist",
                ),
                className="form-check fancyChecklistInDialog",
            ),
            html.Br(),
            html.H5("Layout algorithm"),
            html.Div(
                [
                    html.Div(
                        dbc.RadioItems(
                            options=[
                                {
                                    "label": html.Span(
                                        [
                                            html.I(
                                                className="bi bi-arrow-right"
                                            ),
                                            html.Span(
                                                ui_config.DOT_TEXT,
                                                className="iconlbl",
                                            ),
                                        ],
                                        id="dotAlgSpan",
                                    ),
                                    "value": ui_config.LAYOUT_DOT,
                                },
                                {
                                    "label": html.Span(
                                        [
                                            html.I(className="bi bi-snow"),
                                            html.Span(
                                                "sfdp",
                                                className="iconlbl",
                                            ),
                                        ],
                                        id="sfdpAlgSpan",
                                    ),
                                    "value": ui_config.LAYOUT_SFDP,
                                },
                                {
                                    "label": html.Span(
                                        [
                                            html.I(
                                                className="bi bi-arrow-right"
                                            ),
                                            html.Span(
                                                "Dagre",
                                                className="iconlbl",
                                            ),
                                        ],
                                        id="dagreAlgSpan",
                                    ),
                                    "value": ui_config.LAYOUT_DAGRE,
                                },
                                {
                                    "label": html.Span(
                                        [
                                            html.I(className="bi bi-snow"),
                                            html.Span(
                                                "fCoSE",
                                                className="iconlbl",
                                            ),
                                        ],
                                        id="fcoseAlgSpan",
                                    ),
                                    "value": ui_config.LAYOUT_FCOSE,
                                },
                            ],
                            value=ui_config.DEFAULT_LAYOUT_ALG,
                            className="btn-group",
                            inputClassName="btn-check",
                            labelClassName="btn btn-outline-dark layout-alg-btn",
                            labelCheckedClassName="active",
                            id="layoutAlgRadio",
                        ),
                        className="btn-opt-group",
                        style={
                            "margin-top": "0.75em",
                            "margin-bottom": "0.75em",
                        },
                    ),
                    html.Div(
                        default_dot_alg_desc,
                        id="dotAlgDesc",
                        className=css_config.ALG_DESC_CLASSES
                        + (
                            " removedEntirely"
                            if ui_config.DEFAULT_LAYOUT_ALG
                            != ui_config.LAYOUT_DOT
                            else ""
                        ),
                    ),
                    html.Div(
                        html.P(
                            [
                                "Force-directed layout algorithm described in ",
                                html.A(
                                    "Hu 2005",
                                    href="http://yifanhu.net/PUB/graph_draw_small.pdf",
                                    target="_blank",
                                ),
                                ' ("Efficient and high quality force-directed graph '
                                'drawing").',
                            ]
                        ),
                        id="sfdpAlgDesc",
                        className=css_config.ALG_DESC_CLASSES
                        + (
                            " removedEntirely"
                            if ui_config.DEFAULT_LAYOUT_ALG
                            != ui_config.LAYOUT_SFDP
                            else ""
                        ),
                    ),
                    html.Div(
                        DAGRE_ALG_DESC,
                        id="dagreAlgDesc",
                        className=css_config.ALG_DESC_CLASSES
                        + (
                            " removedEntirely"
                            if ui_config.DEFAULT_LAYOUT_ALG
                            != ui_config.LAYOUT_DAGRE
                            else ""
                        ),
                    ),
                    html.Div(
                        FCOSE_ALG_DESC,
                        id="fcoseAlgDesc",
                        className=css_config.ALG_DESC_CLASSES
                        + (
                            " removedEntirely"
                            if ui_config.DEFAULT_LAYOUT_ALG
                            != ui_config.LAYOUT_FCOSE
                            else ""
                        ),
                    ),
                ],
                style={"text-align": "center"},
            ),
            html.Br(),
            html.H5("Layout parameters"),
            html.Div(
                [
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText(
                                html.Span(
                                    [
                                        html.A(
                                            "Rank separation",
                                            href="https://graphviz.org/docs/attrs/ranksep/",
                                            target="_blank",
                                        ),
                                        " (",
                                        ui_config.DOT_TEXT,
                                        " only)",
                                    ],
                                ),
                            ),
                            dbc.Input(
                                type="text",
                                id="dotRanksep",
                                value=ui_config.NODECENTRIC_2_DEFAULT_DOT_RANKSEP[
                                    node_centric
                                ],
                                className="short-num-input",
                            ),
                        ],
                        size="sm",
                    ),
                    ui_config.OPTIONS_SEP,
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText(
                                html.Span(
                                    [
                                        html.Span(
                                            "K",
                                            style={"font-style": "italic"},
                                        ),
                                        " (",
                                        html.A(
                                            "spring constant",
                                            href="https://graphviz.org/docs/attrs/K/",
                                            target="_blank",
                                        ),
                                        ", sfdp only)",
                                    ],
                                ),
                            ),
                            dbc.Input(
                                type="text",
                                id="sfdpK",
                                value=0.3,
                                className="short-num-input",
                            ),
                        ],
                        size="sm",
                    ),
                    ui_config.OPTIONS_SEP,
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText(
                                html.Span(
                                    [
                                        html.A(
                                            "Overlap scaling factor",
                                            href="https://graphviz.org/docs/attrs/overlap_scaling/",
                                            target="_blank",
                                        ),
                                        " (sfdp only)",
                                    ],
                                ),
                            ),
                            dbc.Input(
                                type="text",
                                id="sfdpOverlapScaling",
                                value=-10,
                                className="short-num-input",
                            ),
                        ],
                        size="sm",
                    ),
                ],
                style={
                    "margin-top": "0.75em",
                },
            ),
        ],
    )


def get_style_options_tab(node_centric):
    return html.Div(
        [
            html.Div(
                [
                    'Click "',
                    html.Span(
                        "Apply",
                        className="text-success",
                    ),
                    '" to make these settings take effect.',
                ],
                className="drawing-option-topnote",
            ),
            html.H5("When a node is selected..."),
            html.Div(
                dcc.Checklist(
                    options=[
                        {
                            "label": "Darken it",
                            "value": ui_config.SELECTED_NODE_DARKEN,
                        },
                        {
                            "label": "Show a border around it",
                            "value": ui_config.SELECTED_NODE_BORDER,
                        },
                    ],
                    value=ui_config.DEFAULT_SELECTED_NODE_SETTINGS,
                    id="selectedNodeSettingsChecklist",
                ),
                className="form-check fancyChecklistInDialog",
            ),
            html.Br(),
            html.H5("How thick should edges be?"),
            html.P("(These values are given in pixels.)"),
            html.H6("Real edges"),
            dbc.InputGroup(
                [
                    dbc.InputGroupText(html.Span("Default")),
                    dbc.Input(
                        type="text",
                        id="realDefaultEdgeWidth",
                        value=ui_config.NODECENTRIC_2_REAL_DEFAULT_EDGEWIDTH[
                            node_centric
                        ],
                        className="short-num-input",
                    ),
                    dbc.InputGroupText(html.Span("Selected")),
                    dbc.Input(
                        type="text",
                        id="realSelectedEdgeWidth",
                        value=ui_config.NODECENTRIC_2_REAL_SELECTED_EDGEWIDTH[
                            node_centric
                        ],
                        className="short-num-input",
                    ),
                ],
                size="sm",
                style={"margin-bottom": "1em"},
            ),
            html.H6("Fake edges"),
            dbc.InputGroup(
                [
                    dbc.InputGroupText(html.Span("Default")),
                    dbc.Input(
                        type="text",
                        id="fakeDefaultEdgeWidth",
                        value=ui_config.NODECENTRIC_2_FAKE_DEFAULT_EDGEWIDTH[
                            node_centric
                        ],
                        className="short-num-input",
                    ),
                    dbc.InputGroupText(html.Span("Selected")),
                    dbc.Input(
                        type="text",
                        id="fakeSelectedEdgeWidth",
                        value=ui_config.NODECENTRIC_2_FAKE_SELECTED_EDGEWIDTH[
                            node_centric
                        ],
                        className="short-num-input",
                    ),
                ],
                size="sm",
            ),
            html.Div(
                html.Button(
                    [
                        html.I(className="bi bi-pen-fill"),
                        html.Span(
                            "Apply",
                            className="iconlbl",
                        ),
                    ],
                    id="applyStyleOptionsButton",
                    className="btn btn-success",
                    type="button",
                ),
                style={"text-align": "right", "margin-top": "1em"},
            ),
        ]
    )
