import re
import time
from collections import defaultdict
from dash import html
from . import css_config, ui_config
from .errors import UIError, WeirdError


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
                        html.Td(fmt_qty(ag.total_seq_len)),
                        html.Td(fmt_qty(ag.n50)),
                    ]
                ),
            ]
        ),
        className=css_config.INFO_DIALOG_TABLE_CLASSES,
    )


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


def add_toast(
    toasts,
    title_text="Error",
    body_text=None,
    body_html=None,
    icon="bi-exclamation-lg",
    header_color=None,
):
    if toasts is None:
        toasts = []
    new_toast = create_toast(
        title_text=title_text,
        body_text=body_text,
        body_html=body_html,
        icon=icon,
        header_color=header_color,
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
                        className="iconlbl me-auto toast-title",
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


def _get_range_text(r):
    # We assume r is a continuous range of integers. It can contain a single
    # element.
    first_ele = f"#{r[0]:,}"
    if len(r) == 1:
        return first_ele
    else:
        return f"{first_ele} \u2013 {r[-1]:,}"


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


def summarize_undrawn_nodes(undrawn_nodes, nn2ccnum, num_searched_for_nodes):
    """Produces a HTML summary of undrawn nodes, to be shown after searching.

    This is used when creating a toast message indicating an error or warning
    arising from searching from nodes that are not currently drawn.
    """
    if len(undrawn_nodes) == 1:
        n = undrawn_nodes[0]
        c = nn2ccnum[n]
        return html.Div(
            f'Node "{n}" is not currently drawn. It\'s in component #{c:,}.',
            className="toast-body",
        )
    else:
        num_undrawn = len(undrawn_nodes)
        if num_searched_for_nodes == num_undrawn:
            s1 = "None of these nodes are currently drawn."
        else:
            s1 = (
                f"{num_undrawn:,} / {num_searched_for_nodes:,} nodes are not "
                "currently drawn."
            )

        undrawn_cc_to_nodes = defaultdict(list)
        for n in undrawn_nodes:
            undrawn_cc_to_nodes[nn2ccnum[n]].append(n)

        if len(undrawn_cc_to_nodes) == 1:
            cnoun = "component"
        else:
            cnoun = "components"
        cc_html_eles = [html.Div(f"{s1} They are in the following {cnoun}:")]
        for c in sorted(undrawn_cc_to_nodes):
            node_list = get_fancy_node_name_list(
                undrawn_cc_to_nodes[c], quote=False
            )
            cc_html_eles.append(html.Div(f"#{c:,}: {node_list}"))
        return html.Div(cc_html_eles, className="toast-body")


def get_screenshot_basename():
    # this should be ISO 8601 compliant. See https://xkcd.com/1179, lol.
    # I am sure there are better ways to represent this tho... if whoever is
    # reading this has strong opinions feel free to open a github issue
    return time.strftime("mgsc-%Y%m%dT%H%M%S")
