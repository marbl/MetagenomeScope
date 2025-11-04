import matplotlib
from dash import html
from . import css_config
from .misc_utils import fmt_qty


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
