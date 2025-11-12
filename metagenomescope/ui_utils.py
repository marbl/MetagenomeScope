import matplotlib
from dash import html
from . import css_config, cy_config, ui_config
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
    # adding the new toast BEFORE the other toasts does put it on top if any
    # others are still on the screen, but it causes weird behavior if any
    # other toasts have been hidden (probably due to bootstrap css/js details).
    # easier to just put the newest toast at the bottom. probably there will
    # only be like 1-2 of these visible at a time for most users anyway
    return toasts + [new_toast]


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
        # yeah yeah i know including an en dash literally in the code is sloppy
        # but stuff like &ndash; doesn't work unless we update HTML source
        # directly and that seems more jank than this
        msg += f"Must be in the range 1 – {len(ag.components)}."
    else:
        msg += (
            "I mean, like, your graph only has one component, so... "
            'this should always be a "1"...'
        )
    return msg


def get_cyjs_stylesheet(
    node_coloring=ui_config.DEFAULT_NODE_COLORING,
    edge_coloring=ui_config.DEFAULT_EDGE_COLORING,
):
    stylesheet = [
        {
            "selector": "node",
            "style": {
                "background-color": cy_config.NODE_COLOR,
                "color": cy_config.UNSELECTED_NODE_FONT_COLOR,
                "label": "data(label)",
                "text-valign": "center",
                "min-zoomed-font-size": "12",
                "z-index": "2",
            },
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "line-color": cy_config.EDGE_COLOR,
                "target-arrow-color": cy_config.EDGE_COLOR,
            },
        },
        {
            "selector": "node:selected",
            "style": {
                "color": cy_config.SELECTED_NODE_FONT_COLOR,
                "background-blacken": cy_config.SELECTED_NODE_BLACKEN,
            },
        },
        {
            "selector": "node.fwd",
            "style": {
                "shape": "polygon",
                "shape-polygon-points": cy_config.FWD_NODE_POLYGON_PTS,
            },
        },
        {
            "selector": "node.rev",
            "style": {
                "shape": "polygon",
                "shape-polygon-points": cy_config.REV_NODE_POLYGON_PTS,
            },
        },
        {
            "selector": "node.unoriented",
            "style": {
                "shape": cy_config.UNORIENTED_NODE_SHAPE,
            },
        },
    ]

    if node_coloring == ui_config.COLORING_RANDOM:
        for i, c in enumerate(cy_config.RANDOM_COLORS):
            stylesheet.append(
                {
                    "selector": f"node.noderand{i}",
                    "style": {
                        "background-color": c,
                    },
                }
            )
    # yeah yeah yeah this is slightly inefficient if both nodes and edges have
    # random coloring because then we're iterating through
    # cy_config.RANDOM_COLORS twice instead of once. there is no way that will
    # ever be a bottleneck.
    if edge_coloring == ui_config.COLORING_RANDOM:
        for i, c in enumerate(cy_config.RANDOM_COLORS):
            stylesheet.append(
                {
                    "selector": f"edge.edgerand{i}",
                    "style": {
                        "line-color": c,
                        "target-arrow-color": c,
                    },
                }
            )

    # Apply a unique color to selected edges. Do this last so it takes
    # precedence over even random edge colorings.
    stylesheet.append(
        {
            "selector": "edge:selected",
            "style": {
                "line-color": cy_config.SELECTED_EDGE_COLOR,
                "target-arrow-color": cy_config.SELECTED_EDGE_COLOR,
            },
        }
    )
    return stylesheet
