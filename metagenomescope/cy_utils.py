from . import cy_config, ui_config, config
from .layout import layout_config
from .errors import WeirdError


def get_cyjs_stylesheet(
    labels,
    node_label_settings,
    edge_label_settings,
    label_font_size,
    expand_settings,
    node_coloring=ui_config.DEFAULT_NODE_COLORING,
    edge_coloring=ui_config.DEFAULT_EDGE_COLORING,
):
    if ui_config.LABELS_EXPAND_PATTERNS in expand_settings:
        do_expand = "include"
    else:
        do_expand = "exclude"
    stylesheet = [
        # nodes
        {
            "selector": "node.nonpattern",
            "style": {
                "background-color": cy_config.NODE_COLOR,
                "color": cy_config.NODE_FONT_COLOR,
                "z-index": "1",
                "z-index-compare": "manual",
                "width": "data(w)",
                "height": "data(h)",
            },
        },
        {
            "selector": "node.nonpattern:selected",
            "style": {
                "border-width": cy_config.SELECTED_NODE_BORDER_WIDTH,
                "border-color": cy_config.SELECTED_NODE_BORDER_COLOR,
                "z-index": "2",
                "z-index-compare": "manual",
            },
        },
        ###### Forward-oriented nodes (pentagons pointing right)
        {
            "selector": "node.fwd.splitN",
            "style": {
                "shape": "polygon",
                "shape-polygon-points": cy_config.FWD_NODE_SPLITN_POLYGON_PTS,
            },
        },
        {
            "selector": "node.fwd.splitL",
            "style": {
                "shape": "rectangle",
            },
        },
        {
            "selector": "node.fwd.splitR",
            "style": {
                "shape": "polygon",
                "shape-polygon-points": cy_config.FWD_NODE_SPLITR_POLYGON_PTS,
            },
        },
        ###### Reverse-oriented nodes (pentagons pointing left)
        {
            "selector": "node.rev.splitN",
            "style": {
                "shape": "polygon",
                "shape-polygon-points": cy_config.REV_NODE_SPLITN_POLYGON_PTS,
            },
        },
        {
            "selector": "node.rev.splitL",
            "style": {
                "shape": "polygon",
                "shape-polygon-points": cy_config.REV_NODE_SPLITL_POLYGON_PTS,
            },
        },
        {
            "selector": "node.rev.splitR",
            "style": {
                "shape": "rectangle",
            },
        },
        ###### Unoriented nodes (circles)
        # ok yeah you could argue that nodes in de Bruijn graphs also have
        # "orientations" but the convention is to draw them like circles
        # because really the edges have the sequences we care about
        {
            "selector": "node.unoriented.splitN",
            "style": {
                "shape": "ellipse",
            },
        },
        {
            "selector": "node.unoriented.splitL",
            "style": {
                "shape": "polygon",
                "shape-polygon-points": cy_config.UNORIENTED_NODE_SPLITL_POLYGON_PTS,
            },
        },
        {
            "selector": "node.unoriented.splitR",
            "style": {
                "shape": "polygon",
                "shape-polygon-points": cy_config.UNORIENTED_NODE_SPLITR_POLYGON_PTS,
            },
        },
        # patterns
        {
            "selector": "node.pattern",
            "style": {
                "shape": "rectangle",
                "border-width": cy_config.UNSELECTED_PATTERN_BORDER_WIDTH,
                "border-color": cy_config.UNSELECTED_PATTERN_BORDER_COLOR,
                "compound-sizing-wrt-labels": do_expand,
                "padding": layout_config.CLUSTER_PADDING,
            },
        },
        {
            "selector": "node.pattern:selected",
            "style": {
                "border-width": cy_config.SELECTED_PATTERN_BORDER_WIDTH,
                "border-color": cy_config.SELECTED_PATTERN_BORDER_COLOR,
            },
        },
        {
            "selector": "node.bubble",
            "style": {
                "background-color": config.PT2COLOR[config.PT_BUBBLE],
            },
        },
        {
            "selector": "node.frayedrope",
            "style": {
                "background-color": config.PT2COLOR[config.PT_FRAYEDROPE],
            },
        },
        {
            "selector": "node.bipartite",
            "style": {
                "background-color": config.PT2COLOR[config.PT_BIPARTITE],
            },
        },
        {
            "selector": "node.chain",
            "style": {
                "background-color": config.PT2COLOR[config.PT_CHAIN],
            },
        },
        {
            "selector": "node.cyclicchain",
            "style": {
                "background-color": config.PT2COLOR[config.PT_CYCLICCHAIN],
            },
        },
        # edges
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "line-color": cy_config.EDGE_COLOR,
                "target-arrow-color": cy_config.EDGE_COLOR,
                "color": cy_config.EDGE_FONT_COLOR,
            },
        },
        {
            "selector": "edge.withctrlpts",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": "data(cpd)",
                "control-point-weights": "data(cpw)",
                "edge-distances": "node-position",
            },
        },
        {
            "selector": "edge.fake",
            "style": {
                "line-style": cy_config.FAKE_EDGE_LINE_STYLE,
                "line-dash-pattern": cy_config.FAKE_EDGE_LINE_DASH_PATTERN,
                "width": cy_config.FAKE_EDGE_WIDTH,
            },
        },
        {
            "selector": "edge:loop",
            "style": {
                # imitate how dot lays out loop edges, where the edge kinda
                # protrudes from the top of the node (see the flye yeast
                # test for an example)
                "source-endpoint": "90deg",
                "target-endpoint": "-90deg",
                "control-point-step-size": 45,
                "loop-direction": "0deg",
                "loop-sweep": "-45deg",
                # loop edges go above nodes. this is mainly here to help with
                # loop edges on long nodes (e.g. -76 in the E. coli test graph)
                # which can intersect with the node body. I think otherwise
                # keeping edges below nodes (as is the Cytoscape.js default)
                # makes sense since it makes clicking on nodes easier
                "z-index": "3",
                "z-index-compare": "manual",
            },
        },
    ]

    labelstyle = cy_config.LABEL_STYLE.copy()
    labelstyle["fontSize"] = f"{label_font_size}em"
    if ui_config.NODE_LABELS in labels:
        # yeah yeah i know that literally the first entry in the stylesheet
        # is node.nonpattern so we could just say stylesheet[0].update()...
        # or something. But I don't want to hardcode reliance on that - seems
        # brittle.
        for sty in stylesheet:
            if sty["selector"] == "node.nonpattern":
                nodelabelstyle = {}
                nodelabelstyle.update(labelstyle)
                if ui_config.LABEL_OFFSET in node_label_settings:
                    nodelabelstyle["text-valign"] = "top"
                else:
                    nodelabelstyle["text-valign"] = "center"
                if ui_config.LABEL_OUTLINE in node_label_settings:
                    nodelabelstyle["text-outline-color"] = "#fff"
                    nodelabelstyle["text-outline-width"] = 1
                    stylesheet.append(
                        {
                            "selector": "node.nonpattern:selected",
                            "style": {
                                "text-outline-color": cy_config.SELECTED_OBJ_OUTLINE_COLOR,
                            },
                        }
                    )
                sty["style"].update(nodelabelstyle)
                break

    if ui_config.EDGE_LABELS in labels:
        edgelabelstyle = {}
        edgelabelstyle.update(labelstyle)
        if ui_config.LABEL_OFFSET in edge_label_settings:
            edgelabelstyle["text-margin-y"] = -4
        if ui_config.LABEL_OUTLINE in edge_label_settings:
            edgelabelstyle["text-outline-color"] = "#fff"
            edgelabelstyle["text-outline-width"] = 1
        if ui_config.LABEL_AUTOROTATE_EDGE in edge_label_settings:
            edgelabelstyle["text-rotation"] = "autorotate"
        stylesheet.append(
            {
                "selector": "edge.real",
                "style": edgelabelstyle,
            }
        )
        # Make selected loop edges semitransparent, to make it easier to view
        # the labels associated with selected loop edges when there are many
        # parallel loops on the same node (this is the case for e.g. the Flye
        # yeast test graph). It's not currently possible to draw edge labels
        # on a higher z-index than edges themselves
        # (https://github.com/cytoscape/cytoscape.js/issues/1900) so this
        # works around that.
        stylesheet.append(
            {
                "selector": "edge:loop:selected",
                "style": {
                    "line-opacity": 0.7,
                },
            }
        )
        # we need to add this after the above edge.real selector in order to
        # get this to take precedence
        if ui_config.LABEL_OUTLINE in edge_label_settings:
            stylesheet.append(
                {
                    "selector": "edge.real:selected",
                    "style": {
                        "text-outline-color": cy_config.SELECTED_OBJ_OUTLINE_COLOR,
                    },
                }
            )

    if ui_config.PATTERN_LABELS in labels:
        for sty in stylesheet:
            if sty["selector"] == "node.pattern":
                sty["style"].update(labelstyle)
                sty["style"].update(cy_config.PATTERN_LABEL_STYLE)
                break

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
    elif edge_coloring == ui_config.COLORING_GRAPH:
        stylesheet.append(
            {
                # [color] only matches edges with a defined data(color)
                # this means that other edges will fall back to the default
                "selector": "edge.real[color]",
                "style": {
                    "line-color": "data(color)",
                    "target-arrow-color": "data(color)",
                },
            }
        )

    # Apply styles to selected edges. Do this last so it takes
    # precedence over even random edge colorings.
    stylesheet.append(
        {
            "selector": "edge:selected",
            "style": {
                "line-color": cy_config.SELECTED_EDGE_COLOR,
                "target-arrow-color": cy_config.SELECTED_EDGE_COLOR,
                "width": cy_config.SELECTED_EDGE_WIDTH,
                "color": cy_config.SELECTED_EDGE_FONT_COLOR,
                "z-index": "4",
                "z-index-compare": "manual",
            },
        }
    )
    stylesheet.append(
        {
            "selector": "edge.fake:selected",
            "style": {
                "width": cy_config.SELECTED_FAKE_EDGE_WIDTH,
            },
        },
    )
    return stylesheet


def get_cyjs_layout_params(layout_alg, draw_settings):
    """Gets layout parameters for Cytoscape.js for a given algorithm."""

    anim_settings = layout_config.ANIMATION_SETTINGS
    anim_settings["animate"] = ui_config.DO_LAYOUT_ANIMATION in draw_settings

    if layout_alg == ui_config.LAYOUT_DAGRE:
        return {"name": "dagre", "rankDir": "LR", **anim_settings}
    elif layout_alg == ui_config.LAYOUT_FCOSE:
        return {"name": "fcose", **anim_settings}
    elif layout_alg in ui_config.LAYOUT2GVPROG:
        return {"name": "preset"}
    else:
        raise WeirdError(f"Unrecogized layout algorithm: {layout_alg}")
