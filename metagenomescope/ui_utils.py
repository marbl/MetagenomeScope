import time
from dash import html
from . import css_config


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


def get_cc_size_rank_error_msg(ag):
    msg = "Invalid component size rank specified. "
    if len(ag.components) > 1:
        msg += f"Must be in the range 1 \u2013 {len(ag.components)}."
    else:
        msg += (
            "I mean, like, your graph only has one component, so... "
            'this should always be a "1"...'
        )
    return msg


def _get_range_text(r):
    # We assume r is a continuous range of integers. It can contain a single
    # element.
    first_ele = f"#{r[0]:,}"
    if len(r) == 1:
        return first_ele
    else:
        return f"{first_ele} \u2013 #{r[-1]:,}"


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
    return " / ".join(range_texts)
