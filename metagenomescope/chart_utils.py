import base64
import matplotlib
import dash_bootstrap_components as dbc
import wotplot as wp
from io import BytesIO
from statistics import mean
from dash import html
from matplotlib import pyplot
from . import ui_config, seq_utils
from .errors import WeirdError, UIError

# turn off matplotlib warning: https://stackoverflow.com/a/74471578
matplotlib.use("agg")


def get_eqn_parts(node_centric):
    if node_centric:
        n = "n"
        objs = "Nodes"
    else:
        n = "e"
        objs = "Edges"
    return n, objs


def get_total_length_latex(node_centric, incl_dollarsigns=True):
    n, objs = get_eqn_parts(node_centric)
    lenaxislatex_inner = (
        r"\sum_{"
        f"{n} "
        r"\in \text{"
        f"{objs}"
        r"}}\text{Length}("
        f"{n}"
        r")"
    )
    if incl_dollarsigns:
        return "$" + lenaxislatex_inner + "$"
    else:
        return lenaxislatex_inner


def get_weightedavg_cov_latex(node_centric, cov_field):
    n, objs = get_eqn_parts(node_centric)
    coverage = ui_config.COVATTR2TITLE[cov_field]
    totallen = get_total_length_latex(node_centric, False)
    return (
        r"$\dfrac{"
        r"\sum_{"
        f"{n} "
        r"\in \text{"
        f"{objs}"
        r"}}"
        r"\text{"
        f"{coverage}"
        r"}("
        f"{n}"
        r") \times \text{Length}("
        f"{n}"
        r")}{"
        f"{totallen}"
        r"}$"
    )


def get_unweightedavg_cov_latex(node_centric, cov_field):
    # assumes node centric, i.e. nodes have lengths and (if we are resorting
    # to not weighting covs in this plot) that edges have covs
    if not node_centric:
        raise WeirdError("we don't support this yet")
    else:
        coverage = ui_config.COVATTR2TITLE[cov_field]
        return (
            r"$\dfrac{"
            r"\sum_{"
            "e "
            r"\in \text{"
            "Edges"
            r"}}"
            r"\text{"
            f"{coverage}"
            r"}("
            "e"
            r")}{|"
            r"\text{Edges}"
            r"|}$"
        )


def get_plot_missing_data_msg(num, den, noun, reason):
    if num > 0:
        # now THIS is obsessive compulsive disorder
        if num == 1:
            s = ""
            are = "is"
        else:
            s = "s"
            are = "are"
        mpct = 100 * (num / den)
        missing_info = [
            html.Span(
                f"{num:,} / {den:,} ({mpct:.2f}%) {noun}{s}",
                className="fw-bold",
            ),
            f" {are} omitted from this plot due to {reason}.",
        ]
    else:
        missing_info = None
    return missing_info


def prettify_go_fig(fig):
    """Adjusts a plotly.graph_objects figure to make it a bit nicer.

    ...at least for our purposes, and in my opinion.
    """
    fig.update_layout(
        font=dict(size=16),
        # By default the title is shoved up really high above
        # the figure; this repositions it to be closer, while
        # still keeping a bit of padding. From
        # https://community.plotly.com/t/margins-around-graphs/11550/6
        title=dict(yanchor="bottom", y=1, yref="paper"),
        title_pad=dict(b=30),
        margin=dict(t=75),
    )
    # Hack to add padding to the right of the y-axis tick labels:
    # https://stackoverflow.com/a/66736119
    fig.update_yaxes(ticksuffix=" ")


def get_num_bins_option(val_id, btn_id):
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                "Desired maximum # bins",
            ),
            dbc.Input(
                placeholder="# bins", id=val_id, className="long-num-input"
            ),
            dbc.Button("Apply", id=btn_id, color="dark"),
        ],
        size="sm",
    )


def get_max_x_option(val_id, btn_id):
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                "Maximum x value",
            ),
            dbc.Input(
                placeholder="max x", id=val_id, className="long-num-input"
            ),
            dbc.Button("Apply", id=btn_id, color="dark"),
        ],
        size="sm",
    )


def get_scale_options(html_obj_id, desc, default=ui_config.SCALE_LINEAR):
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                desc, className="input-group-text-next-to-radio-button-group"
            ),
            html.Div(
                dbc.RadioItems(
                    options=[
                        {
                            "label": "Linear",
                            "value": ui_config.SCALE_LINEAR,
                        },
                        {
                            "label": "Logarithmic",
                            "value": ui_config.SCALE_LOG,
                        },
                    ],
                    value=default,
                    className="btn-group",
                    inputClassName="btn-check",
                    labelClassName="btn btn-sm btn-outline-dark",
                    labelCheckedClassName="active",
                    id=html_obj_id,
                ),
                className="btn-opt-group",
            ),
        ],
        size="sm",
    )


def get_hist_options(nbins_id, nbins_btn_id, xmax_id, xmax_btn_id, y_scale_id):
    return html.Div(
        [
            get_num_bins_option(nbins_id, nbins_btn_id),
            ui_config.OPTIONS_SEP,
            get_max_x_option(xmax_id, xmax_btn_id),
            ui_config.OPTIONS_SEP,
            get_scale_options(
                y_scale_id, "y-axis scale", default=ui_config.SCALE_LOG
            ),
        ],
    )


def get_node_edge_toggle(html_obj_id):
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                "Show nodes or edges?",
                className="input-group-text-next-to-radio-button-group",
            ),
            html.Div(
                dbc.RadioItems(
                    options=[
                        {
                            "label": "Nodes",
                            "value": ui_config.NODES_HIST,
                        },
                        {
                            "label": "Edges",
                            "value": ui_config.EDGES_HIST,
                        },
                    ],
                    value=ui_config.NODES_HIST,
                    className="btn-group",
                    inputClassName="btn-check",
                    labelClassName="btn btn-sm btn-outline-dark",
                    labelCheckedClassName="active",
                    id=html_obj_id,
                ),
                className="btn-opt-group",
            ),
        ],
        size="sm",
    )


def get_scatterplot_options(x_scale_id, y_scale_id):
    return html.Div(
        [
            get_scale_options(
                x_scale_id, "x-axis scale", default=ui_config.SCALE_LOG
            ),
            ui_config.OPTIONS_SEP,
            get_scale_options(
                y_scale_id, "y-axis scale", default=ui_config.SCALE_LOG
            ),
            ui_config.OPTIONS_SEP,
        ]
    )


def get_treemap_options(ag):
    if ag.orientation_in_name and not ag.is_flye_dot:
        default = ui_config.TREEMAP_SINGLE
        ig_classes = ""
    else:
        # MetaCarvel GML and Flye DOT files don't support decoupling (and
        # MetaCarvel GMLs don't even support the notion of "nonredundant"
        # components), so hide the option for these graphs.
        default = ui_config.TREEMAP_DOUBLE
        ig_classes = " removedEntirely"

    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                "Show only nonredundant components, and decouple strand-tangled components?",
                className="input-group-text-next-to-radio-button-group",
            ),
            html.Div(
                dbc.RadioItems(
                    options=[
                        {
                            "label": "Yes",
                            "value": ui_config.TREEMAP_SINGLE,
                        },
                        {
                            "label": "No",
                            "value": ui_config.TREEMAP_DOUBLE,
                        },
                    ],
                    value=default,
                    className="btn-group",
                    inputClassName="btn-check",
                    labelClassName="btn btn-sm btn-outline-dark",
                    labelCheckedClassName="active",
                    id="ccTreemapType",
                ),
                className="btn-opt-group",
            ),
        ],
        size="sm",
        className=ig_classes,
    )


def get_treemap_title(treemap_type):
    if treemap_type == ui_config.TREEMAP_SINGLE:
        return "Number of nodes per component (nonredundant and decoupled)"
    else:
        return "Number of nodes per component (all components)"


def trim_seq_name(n, is_seq=False, cutoff=8):
    add_ellipsis = False
    if len(n) <= cutoff:
        t = n
    else:
        # note that names with a leading "-" due to representing negative
        # sequences will have the "-" count as a character
        t = n[:cutoff]
        add_ellipsis = True

    if is_seq:
        # to distinguish raw DNA sequences (or whatever, RNA sequences, if
        # we end up supporting that eventually) from ordinary node names or
        # whatever, we format raw sequence names in italics (or, like,
        # technically using $$'s means using math mode in matplotlib, but I've
        # been using this as a way to represent "italics" in my plots for
        # multiple years now and nobody has stopped me yet)
        t = f"${t}$"

    if add_ellipsis:
        t += "..."

    return t


def fmt_internal_spine(s):
    # https://stackoverflow.com/a/12059429
    s.set_color("#bbb")


def compute_space_in_cells(cell_sizes, space):
    # compute the space between subplots, mirroring what matplotlib
    # does: https://matplotlib.org/stable/api/_as_gen/matplotlib.gridspec.GridSpec.html
    # If we don't account for this, then this would mean assuming that
    # the amount of space available to draw the plot is bigger than it
    # actually is -- resulting in us drawing markers that are too big.
    if space > 0:
        # If there are N plots along this axis, then there are (N - 1)
        # gaps between them. Just like how you have 5 fingers on one of your
        # hands, but 4 gaps between each of these fingers. Um, probably.
        # Anyway that's why the - 1.
        return space * mean(cell_sizes) * (len(cell_sizes) - 1)
    return 0


def compute_dot_plot_size(wcells, hcells, space):

    wcelltotal = sum(wcells)
    hcelltotal = sum(hcells)

    # Constrain the longest dimension of the plot to a fixed size, then
    # adjust the other dimension in such a way that keeps the aspect ratio
    # fixed. (Otherwise, the plot looks weird.)
    # TODO: Eventually would be nice to allow the plot to get bigger as needed
    long_dim_size = 7
    if wcelltotal > hcelltotal:
        width = long_dim_size
        height = long_dim_size * (hcelltotal / wcelltotal)
        space_in_cells = compute_space_in_cells(wcells, space)
    else:
        height = long_dim_size
        width = long_dim_size * (wcelltotal / hcelltotal)
        space_in_cells = compute_space_in_cells(hcells, space)

    # (Longest axis length) * (points per inch), divided by total # cells
    # along this axis.
    markersize = (long_dim_size * ui_config.POINTS_PER_INCH_MATPLOTLIB) / (
        space_in_cells + max(wcelltotal, hcelltotal)
    )
    # When the sequences get really big, these marks can become hard to see;
    # bump them up
    markersize = max(markersize, ui_config.MIN_MARKERSIZE)
    return width, height, markersize


def create_dot_plot(
    seqs1,
    seqs2,
    names1,
    names2,
    k=ui_config.K_DEFAULT,
    autoselect_k=True,
    space=ui_config.SPACE_DEFAULT,
):

    lens1 = [len(s) for s in seqs1]
    lens2 = [len(s) for s in seqs2]
    if autoselect_k:
        k = seq_utils.autoselect_dotplot_k(lens1, lens2)

    nonzero_space = space > 0

    # Figure out how much space, relatively, to allocate per sequence.
    # Especially for small sequences, we need to account for the trailing
    # k here -- otherwise the plots get messed up and things aren't
    # perfectly flush with each other.
    width_ratios = [seqlen - k + 1 for seqlen in lens1]
    # the y = 0-th subplot is the top one! So we need to reverse the
    # sequences here.
    height_ratios = [seqlen - k + 1 for seqlen in lens2[::-1]]

    fig, axes = pyplot.subplots(
        len(seqs2),
        len(seqs1),
        gridspec_kw={
            "hspace": space,
            "wspace": space,
            "height_ratios": height_ratios,
            "width_ratios": width_ratios,
        },
        # Make subplots() always return a 2D array of Axes objects, even if
        # only one sequence is given the x- and/or y-axis. This makes accessing
        # subplots programmatically easier when we don't know how many
        # sequences there are going to be. https://stackoverflow.com/a/72766334
        squeeze=False,
    )

    w, h, ms = compute_dot_plot_size(width_ratios, height_ratios, space)
    fig.set_size_inches(w, h)

    try:
        for xi, xs in enumerate(seqs1):
            for yi, ys in enumerate(seqs2):
                ys = seqs2[yi]
                if len(xs) + len(ys) > 15e6:
                    # see wotplot docs. slower, but uses less memory
                    suff_only = True
                else:
                    # for shorter sequences, this is fine
                    suff_only = False
                m = wp.DotPlotMatrix(xs, ys, k, suff_only=suff_only)

                # When yi = 0, we are working with the first sequence in
                # seqs2 -- which will be drawn on the bottommost row of the
                # grid of plots. However, since matplotlib uses y = 0 for
                # the top row, we have to take this into account in how we
                # access the Axes object for this plot.
                ax = axes[len(seqs2) - 1 - yi, xi]
                wp.viz_spy(
                    m,
                    ax=ax,
                    s1_name=names1[xi],
                    s2_name=names2[yi],
                    markersize=ms,
                )

                # Adjust labels, and hide / recolor certain plot boundaries
                # (aka spines)
                if xi == 0:
                    # Get rid of length & arrow in dot plot grids, for now
                    if len(seqs2) > 1:
                        # https://stackoverflow.com/questions/27671748#comment72696121_42743706
                        ax.set_ylabel(
                            names2[yi],
                            fontsize=8,
                            rotation=0,
                            ha="right",
                            va="center",
                        )
                else:
                    ax.set_ylabel("")
                    fmt_internal_spine(ax.spines["left"])

                if xi != len(seqs1) - 1:
                    if nonzero_space:
                        fmt_internal_spine(ax.spines["right"])
                    else:
                        ax.spines["right"].set_visible(False)

                if yi == 0:
                    if len(seqs1) > 1:
                        # Align the endpoint of the label with the center of
                        # the subplot: https://stackoverflow.com/a/67459618
                        ax.set_xlabel(
                            names1[xi],
                            fontsize=8,
                            rotation=45,
                            ha="right",
                            rotation_mode="anchor",
                        )
                else:
                    ax.set_xlabel("")
                    if nonzero_space:
                        fmt_internal_spine(ax.spines["bottom"])
                    else:
                        ax.spines["bottom"].set_visible(False)

                if yi != len(seqs2) - 1:
                    fmt_internal_spine(ax.spines["top"])
    except ValueError as ei:
        # If wotplot throws an error (e.g. due to a sequence being
        # shorter than a manually selected k-mer size, or containing
        # invalid characters), show it to the user as a toast message.
        raise UIError(str(ei))

    # Convert matplotlib output to a base 64 string so that it can be used
    # as the source of an img tag: https://plotly.com/blog/dash-matplotlib/
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    fig_b64 = base64.b64encode(buf.getbuffer()).decode("ascii")
    fig_b64_s = f"data:image/png;base64,{fig_b64}"
    # Prevent matplotlib from keeping old stuff in memory (if we don't do
    # this, you'll see a warning after creating 20 images -- or at least
    # that is what happens in october 2026 ._.)
    pyplot.close("all")

    return fig_b64_s
