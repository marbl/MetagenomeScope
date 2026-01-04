from . import cy_config, ui_config


def get_cyjs_stylesheet(
    node_coloring=ui_config.DEFAULT_NODE_COLORING,
    edge_coloring=ui_config.DEFAULT_EDGE_COLORING,
):
    stylesheet = [
        # nodes
        {
            "selector": "node.nonpattern",
            "style": {
                "background-color": cy_config.NODE_COLOR,
                "color": cy_config.UNSELECTED_NODE_FONT_COLOR,
                "label": "data(label)",
                "text-valign": "center",
                "min-zoomed-font-size": "12",
                "z-index": "1",
                "z-index-compare": "manual",
            },
        },
        {
            "selector": "node.fwd, node.rev",
            "style": {
                "width": "data(w)",
                "height": "data(h)",
            },
        },
        {
            # TODO maybe resize to accommodate large LJA node labels
            "selector": "node.unoriented",
            "style": {
                "width": "30",
                "height": "30",
            },
        },
        {
            "selector": "node.nonpattern:selected",
            "style": {
                "border-width": cy_config.SELECTED_NODE_BORDER_WIDTH,
                "border-color": cy_config.SELECTED_NODE_BORDER_COLOR,
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
                "shape": "polygon",
                "shape-polygon-points": cy_config.FWD_NODE_SPLITL_POLYGON_PTS,
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
                "shape": "polygon",
                "shape-polygon-points": cy_config.REV_NODE_SPLITR_POLYGON_PTS,
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
                "background-color": cy_config.BUBBLE_COLOR,
            },
        },
        {
            "selector": "node.frayedrope",
            "style": {
                "background-color": cy_config.FRAYEDROPE_COLOR,
            },
        },
        {
            "selector": "node.chain",
            "style": {
                "background-color": cy_config.CHAIN_COLOR,
            },
        },
        {
            "selector": "node.cyclicchain",
            "style": {
                "background-color": cy_config.CYCLICCHAIN_COLOR,
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
                # makes the loop come out of the node at its right side and
                # enter the node at its left side
                "source-endpoint": "90deg",
                "target-endpoint": "-90deg",
                # loop edges go above nodes. this is mainly here to help with
                # loop edges on long nodes (e.g. -76 in the E. coli test graph)
                # which can intersect with the node body. I think otherwise
                # keeping edges below nodes (as is the Cytoscape.js default)
                # makes sense since it makes clicking on nodes easier
                "z-index": "2",
                "z-index-compare": "manual",
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

    # Apply styles to selected edges. Do this last so it takes
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
