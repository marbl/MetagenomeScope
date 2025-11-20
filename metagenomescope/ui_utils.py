import re
import time
from dash import html
from . import css_config, ui_config
from .errors import UIError


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


def add_error_toast(toasts, title_text="Error", body_text=None):
    if toasts is None:
        toasts = []
    new_toast = get_error_toast(title_text=title_text, body_text=body_text)
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


def get_error_toast(title_text="Error", body_text=None):
    # https://getbootstrap.com/docs/5.3/components/toasts/#live-example
    toast = html.Div(
        [
            # toast header
            html.Div(
                [
                    html.I(className="bi bi-exclamation-lg"),
                    html.Span(
                        title_text,
                        className="iconlbl me-auto",
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
        toast.children.append(html.Div(body_text, className="toast-body"))
    return toast


def get_size_rank_error_msg(ag):
    msg = "Invalid component size rank specified. "
    if len(ag.components) > 1:
        msg += f"Must be in the range 1 \u2013 {len(ag.components)}."
    else:
        msg += (
            "I mean, like, your graph only has one component, so... "
            'this should always be a "1"...'
        )
    return msg


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


def get_size_ranks_from_input(val, ag):
    if val is None or len(val) == 0:
        raise UIError("No component size rank(s) specified.")
    srs = set()
    entries = val.split(",")
    # Each entry e in "entries" can be one of:
    # * a single size rank (e.g. "2")
    # * a range of size ranks (e.g. "2-5")
    # * a half-open range of size ranks (e.g. "-5", "8-")
    #   indicating that we should select all size ranks <= or >= some value
    for e in entries:
        e = e.strip()
        if re.match("^[0-9]+$", e):
            # e is a single size rank
            sr = int(e)
            if sr >= 1 and sr <= len(ag.components):
                srs.add(int(e))
            else:
                raise UIError(
                    f'Out-of-range component size rank "{e}" specified. Must be in '
                    f"the range 1 \u2013 {len(ag.components)}."
                )
        else:
            # e is a range? hopefully???
            r0 = None
            r1 = None
            for d in ui_config.RANGE_DASHES:
                if e.count(d) == 1:
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
                            f'Invalid component size rank range "{e}" '
                            "specified. Please give a start and/or an end for "
                            "the range."
                        )
                    break
            # If none of the acceptable dash characters were present in e,
            # we will end up here -- with r0 and r1 both set to None.
            if r0 is None:
                raise UIError(
                    f'Invalid component size rank or size rank range "{e}" '
                    'specified. Must be either a single number (e.g. "1"), '
                    'a range of numbers (e.g. "2-5"), or a half-open range '
                    'of numbers (e.g. "2-").'
                )
            # Defaults for half-open ranges. "-5" represents [1, 2, 3, 4, 5],
            # and "5-" represents [5, 6, 7, 8, ... len(ag.components)].
            # Thankfully we don't have to worry about the case where both r0
            # and r1 are empty (causing us to draw all ccs), becuase we have
            # already checked above for this specific case.
            i0 = 1 if len(r0) == 0 else None
            i1 = len(ag.components) if len(r1) == 0 else None
            if re.match("^[0-9]+$", r0):
                i0 = int(r0)
                if i0 < 1 or i0 > len(ag.components):
                    i0 = None
            if re.match("^[0-9]+$", r1):
                i1 = int(r1)
                if i1 < 1 or i1 > len(ag.components):
                    i1 = None
            # TODO obvs this is sloppy, abstract shared text
            if i0 is None:
                if i1 is None:
                    raise UIError(
                        f'Invalid component size ranks "{r0}" and "{r1}" '
                        f'in the range "{e}" specified. Must be numbers in '
                        f"the range 1 \u2013 {len(ag.components)}."
                    )
                raise UIError(
                    f'Invalid component size rank "{r0}" '
                    f'in the range "{e}" specified. Must be a number in '
                    f"the range 1 \u2013 {len(ag.components)}."
                )
            elif i1 is None:
                raise UIError(
                    f'Invalid component size rank "{r1}" '
                    f'in the range "{e}" specified. Must be a number in '
                    f"the range 1 \u2013 {len(ag.components)}."
                )
            # add all cc nums in the inclusive interval [i0, i1] to
            # srs. you could make a reasonable point here about how it
            # would be more efficient to just store the range start-/end-
            # points... hmm, maybe we could switch to that eventually,
            # i guess that would actually be doable
            srs.update(range(i0, i1 + 1))
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
    # we MIGHT be able to assume that the input cc nums list is sorted but
    # whatever it's safer to just be paranoid and sort anyway
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
