import matplotlib
from dash import html
from . import css_config
from .misc_utils import fmt_qty, get_toast_timestamp


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


def use_thousands_sep(mpl_axis):
    """Adjusts a matplotlib axis to use thousands separators on tick labels.

    References
    ----------
    Modified from https://stackoverflow.com/a/25973637, and copied from code
    I wrote like 5 years ago (???) now in
    https://github.com/fedarko/sheepgut/blob/main/notebooks/Header.ipynb
    """
    # this is modified to work better with integers: matplotlib seems to store
    # all values as floats internally, even essentially integral things -- so
    # we can use the float.is_integer() method to see if a value is "close
    # enough" to an integer, and if so remove the trailing ".0" that happens
    # when you try to format a float of an integer -- see
    # https://stackoverflow.com/a/21583817.)
    mpl_axis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(
            lambda x, pos: (
                "{:,}".format(int(x)) if x.is_integer() else "{:,}".format(x)
            )
        )
    )


def add_error_toast(toasts, title_text="Error", body_text=None):
    if toasts is None:
        toasts = []
    new_toast = get_error_toast(title_text=title_text, body_text=body_text)
    return [new_toast] + toasts


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
        className="toast fade show",
        role="alert",
        **{
            "aria-live": "assertive",
            "aria-atomic": "true",
            "data-bs-delay": "5000",
        },
    )
    if body_text is not None:
        toast.children.append(html.Div(body_text, className="toast-body"))
    return toast
