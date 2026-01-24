from . import cy_config, ui_config, config
from .layout import layout_config
from .errors import WeirdError


def get_cyjs_stylesheet(
    labels,
    label_font_size,
    node_coloring=ui_config.DEFAULT_NODE_COLORING,
    edge_coloring=ui_config.DEFAULT_EDGE_COLORING,
):
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
                # if a descendant node/edge's label goes outside of the
                # pattern, don't make the pattern bigger to compensate. that
                # will just make the graph look worse imo...
                "compound-sizing-wrt-labels": "exclude",
                # NOTE: if desired we can set padding attrs here to 0 to force
                # node boundaries to be flush with the sides of the pattern -
                # it might help with accuracy stuff when we use graphviz edge
                # ctrl pts. however, i think having some padding is helpful
                # when we are working with patterns containing patterns (esp
                # like a chain of two bubbles)
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
                sty["style"].update(labelstyle)
                sty["style"].update(cy_config.NODE_LABEL_STYLE)
                break

    if ui_config.EDGE_LABELS in labels:
        stylesheet.append(
            {
                "selector": "edge.real",
                "style": {
                    **labelstyle,
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
                "z-index": "3",
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


def get_layout_params(layout_alg, draw_settings):
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
