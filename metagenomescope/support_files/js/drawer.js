define(["jquery", "underscore", "cytoscape", "utils"], function (
    $,
    _,
    cytoscape,
    utils
) {
    class Drawer {
        constructor(cyDivID) {
            this.cyDivID = cyDivID;
            this.cyDiv = $("#" + cyDivID);
            // Instance of Cytoscape.js
            this.cy = null;

            this.bgColor = undefined;
        }

        /**
         * Destroys the instance of Cytoscape.js, in order to prepare for
         * drawing another part of the graph (or just the same part again I
         * guess, since that is the user's prerogative).
         */
        destroyGraph() {
            this.cy.destroy();
        }

        /**
         * Creates an instance of Cytoscape.js to which we can add elements.
         */
        initGraph() {
            // Update the bg color only when we call initGraph(). This ensures
            // that we have the currently-used background color on hand, for
            // stuff like exporting where we need to know the background color
            this.bgColor = $("#bgcp").colorpicker("getValue");
            this.cyDiv.css("background", this.bgColor);
            this.cy = cytoscape({
                container: document.getElementById(this.cyDivID),
                layout: { name: "preset" },
                // TODO: this should be a config-level thing (should we make a
                // Config object or file or whatever?) rather than hardcoded
                // here
                maxZoom: 9,
                // TODO: hideEdgesOnViewport and textureOnViewport
                userPanningEnabled: false,
                userZoomingEnabled: false,
                boxSelectionEnabled: false,
                autounselectify: true,
                autoungrabify: true,
                style: [
                    {
                        selector: "node",
                        style: {
                            width: "data(w)",
                            height: "data(h)",
                        },
                    },
                    // The following few classes are used to set properties of
                    // patterns
                    {
                        selector: "node.pattern",
                        style: {
                            shape: "rectangle",
                            "border-width": 0,
                            "padding-top": 0,
                            "padding-right": 0,
                            "padding-left": 0,
                            "padding-bottom": 0,
                        },
                    },
                    {
                        // Give collapsed patterns a number indicating child count
                        selector: "node.pattern[?isCollapsed]",
                        style: {
                            "min-zoomed-font-size": 12,
                            "font-size": 48,
                            label: "data(interiorNodeCount)",
                            "text-valign": "center",
                            "font-weight": "bold",
                            color: $("#cngcccp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.F",
                        style: {
                            // default color matches 'green2' in graphviz
                            // (but honestly I just picked what I considered to be
                            // the least visually offensive shade of green)
                            "background-color": $("#fropecp").colorpicker(
                                "getValue"
                            ),
                            shape: "polygon",
                            // Defines a "sideways hourglass" pattern.
                            // This is intended to be used when the graph is
                            // displayed from left to right or right to left.
                            // If the graph is rotated, these points should
                            // also be (this distinction is made in the old
                            // codebase -- see the
                            // mgsc.FRAYED_ROPE_LEFTRIGHTDIR and _UPDOWNDIR
                            // variables).
                            //
                            // |\/|
                            // |  |
                            // |/\|
                            "shape-polygon-points":
                                "-1 -1 0 -0.5 1 -1 1 1 0 0.5 -1 1",
                        },
                    },
                    {
                        selector: "node.B",
                        style: {
                            // default color matches 'cornflowerblue' in graphviz
                            "background-color": $("#bubblecp").colorpicker(
                                "getValue"
                            ),
                            shape: "polygon",
                            // Defines a hexagon pattern. Notes about the
                            // polygon points for frayed ropes above apply.
                            //  ___
                            // /   \
                            // \___/
                            "shape-polygon-points":
                                "-1 0 -0.5 -1 0.5 -1 1 0 0.5 1 -0.5 1",
                        },
                    },
                    {
                        selector: "node.C",
                        style: {
                            // default color matches 'salmon' in graphviz
                            "background-color": $("#chaincp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.Y",
                        style: {
                            // default color matches 'darkgoldenrod1' in graphviz
                            "background-color": $("#ychaincp").colorpicker(
                                "getValue"
                            ),
                            shape: "ellipse",
                        },
                    },
                    {
                        selector: "node.M",
                        style: {
                            "background-color": $("#miscpatterncp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        // NOTE: Not currently used but might need to be if
                        // hierarch. pattern decomposition is a bottleneck
                        selector: "node.pattern.pseudoparent",
                        style: {
                            "z-index-compare": "manual",
                            "z-index": 0,
                        },
                    },
                    {
                        selector: "node.bb_enforcing",
                        style: {
                            // Make these nodes invisible
                            "background-opacity": 0,
                            // A width/height of zero just results in Cytoscape.js not
                            // drawing these nodes -- hence a width/height of one
                            width: 1,
                            height: 1,
                        },
                    },
                    {
                        // Nodes with the "basic" class, known in old versions
                        // of MetagenomeScope as "noncluster", are just regular
                        // nodes (i.e. not collapsed patterns that behave like
                        // nodes).
                        selector: "node.basic",
                        style: {
                            label: "data(label)",
                            "text-valign": "center",
                            // rendering text is computationally expensive, so if
                            // we're zoomed out so much that the text would be
                            // illegible (or hard-to-read, at least) then don't
                            // render the text.
                            "min-zoomed-font-size": 12,
                            "z-index": 2,
                            "z-index-compare": "manual",
                        },
                    },
                    {
                        selector: "node.basic.noncolorized",
                        style: {
                            "background-color": $("#usncp").colorpicker(
                                "getValue"
                            ),
                            color: $("#usnlcp").colorpicker("getValue"),
                        },
                    },
                    // TODO: add a generalized "colorized" class or something
                    // for coloring by GC content, coverage, ...
                    {
                        selector: "node.basic.leftdir",
                        style: {
                            // Represents a node pointing left (i.e. in the
                            // reverse direction, if the graph flows from left
                            // to right)
                            //  ___
                            // /   |
                            // \___|
                            shape: "polygon",
                            "shape-polygon-points":
                                "1 1 -0.23587 1 -1 0 -0.23587 -1 1 -1",
                        },
                    },
                    {
                        selector: "node.basic.rightdir",
                        style: {
                            // Represents a node pointing left (i.e. in the
                            // reverse direction, if the graph flows from left
                            // to right)
                            //  ___
                            // |   \
                            // |___/
                            shape: "polygon",
                            "shape-polygon-points":
                                "-1 1 0.23587 1 1 0 0.23587 -1 -1 -1",
                        },
                    },
                    {
                        selector: "node.basic.tentative",
                        style: {
                            "border-width": 5,
                            "border-color": $("#tnbcp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.pattern.tentative",
                        style: {
                            "border-width": 5,
                            "border-color": $("#tngbcp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.currpath",
                        style: {
                            "background-color": $("#cpcp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.basic:selected",
                        style: {
                            "background-color": $("#sncp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.basic.noncolorized:selected",
                        style: {
                            color: $("#snlcp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.basic.gccolorized:selected",
                        style: {
                            color: $("#csnlcp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.pattern:selected",
                        style: {
                            "border-width": 5,
                            "border-color": $("#sngbcp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge",
                        style: {
                            width: "data(thickness)",
                            "line-color": $("#usecp").colorpicker("getValue"),
                            "target-arrow-color": $("#usecp").colorpicker(
                                "getValue"
                            ),
                            "loop-direction": "30deg",
                            "z-index": 1,
                            "z-index-compare": "manual",
                        },
                    },
                    {
                        selector: "edge:selected",
                        style: {
                            "line-color": $("#secp").colorpicker("getValue"),
                            "target-arrow-color": $("#secp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge.oriented",
                        style: {
                            "target-arrow-shape": "triangle",
                            "target-endpoint": "-50% 0%",
                            "source-endpoint": "50% 0",
                        },
                    },
                    {
                        selector: "edge:loop",
                        style: {
                            "z-index": 5,
                        },
                    },
                    {
                        selector: "edge.unoriented_loop",
                        style: {
                            "target-endpoint": "-50% 0%",
                            "source-endpoint": "50% 0",
                        },
                    },
                    {
                        // Used for edges that were assigned valid (i.e. not
                        // just a straight line or self-directed edge)
                        // cpd/cpw properties from the xdot file.
                        selector: "edge.unbundledbezier",
                        style: {
                            "curve-style": "unbundled-bezier",
                            "control-point-distances": "data(cpd)",
                            "control-point-weights": "data(cpw)",
                            "edge-distances": "node-position",
                        },
                    },
                    {
                        // Used for:
                        //  -Self-directed edges
                        //  -Lines that are determined upon parsing the xdot file to
                        //   be sufficiently close to a straight line
                        //  -Temporary edges, for which we have no control point
                        //   data (i.e. any edges directly from/to compound nodes
                        //   during the collapsing process)
                        selector: "edge.basicbezier",
                        style: {
                            "curve-style": "bezier",
                        },
                    },
                    {
                        selector: "edge.virtual",
                        style: {
                            "line-style": "dashed",
                        },
                    },
                    {
                        selector: "edge.high_outlier",
                        style: {
                            "line-color": $("#hoecp").colorpicker("getValue"),
                            "target-arrow-color": $("#hoecp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge.high_outlier:selected",
                        style: {
                            "line-color": $("#hosecp").colorpicker("getValue"),
                            "target-arrow-color": $("#hosecp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge.low_outlier",
                        style: {
                            "line-color": $("#loecp").colorpicker("getValue"),
                            "target-arrow-color": $("#loecp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge.low_outlier:selected",
                        style: {
                            "line-color": $("#losecp").colorpicker("getValue"),
                            "target-arrow-color": $("#losecp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                ],
            });
        }

        /**
         * Draws component(s) in the graph.
         *
         * @param {Array} componentsToDraw 1-indexed size rank numbers of the
         *                                 component(s) to draw.
         *
         * @param {DataHolder} dataHolder Object containing graph data.
         *
         * @throws {Error} If componentsToDraw contains duplicate values and/or
         *                 if any of the numbers within it are invalid with
         *                 respect to the dataHolder. (TODO -- maybe make this
         *                 a dataholder method? validation shouldn't be the
         *                 drawer's problem.)
         */
        draw(componentsToDraw, dataHolder) {
            var scope = this;
            if (!_.isNull(this.cy)) {
                this.destroyGraph();
            }
            this.initGraph();
            this.cy.startBatch();
            // TODO: set graph bindings
            //
            // -Pass each component to DataHolder, and have it give us all the
            // patterns, nodes, and edges to draw for that component. We will
            // need to iterate through each component and then concatenate the
            // positions based on previously drawn components.
            _.each(componentsToDraw, function (sizeRank) {
                var pattAttrs = dataHolder.data.patt_attrs;
                _.each(dataHolder.getPatternsInComponent(sizeRank), function (
                    pattVals,
                    pattID
                ) {
                    var bb = dataHolder.data.components[sizeRank - 1].bb;
                    var bottLeft = [
                        pattVals[pattAttrs.left],
                        pattVals[pattAttrs.bottom],
                    ];
                    var topRight = [
                        pattVals[pattAttrs.right],
                        pattVals[pattAttrs.top],
                    ];
                    var centerPos = [
                        (bottLeft[0] + topRight[0]) / 2,
                        (bottLeft[1] + topRight[1]) / 2,
                    ];
                    var pattData = {
                        id: pattID,
                        w: pattVals[pattAttrs.right] - pattVals[pattAttrs.left],
                        h: pattVals[pattAttrs.top] - pattVals[pattAttrs.bottom],
                        isCollapsed: false,
                    };
                    var classes = "pattern";
                    if (pattVals[pattAttrs.pattern_type] === "chain") {
                        classes += " C";
                    } else if (
                        pattVals[pattAttrs.pattern_type] === "cyclicchain"
                    ) {
                        classes += " Y";
                    } else if (pattVals[pattAttrs.pattern_type] === "bubble") {
                        classes += " B";
                    } else if (
                        pattVals[pattAttrs.pattern_type] === "frayedrope"
                    ) {
                        classes += " F";
                    } else {
                        classes += " M";
                    }
                    scope.cy.add({
                        data: pattData,
                        position: { x: centerPos[0], y: centerPos[1] },
                        classes: classes,
                    });
                });
                var nodeAttrs = dataHolder.data.node_attrs;
                _.each(dataHolder.getNodesInComponent(sizeRank), function (
                    nodeVals,
                    nodeID
                ) {
                    var nodeData = {
                        id: nodeID,
                        label: nodeVals[nodeAttrs.name],
                        length: nodeVals[nodeAttrs.length],
                        // TODO lotta junk here we should preemptively set up
                        // in python
                        w: nodeVals[nodeAttrs.height] * 54,
                        h: nodeVals[nodeAttrs.width] * 54,
                    };
                    var classes = "basic";
                    var orientation = nodeVals[nodeAttrs.orientation];
                    if (orientation === "+") {
                        classes += " rightdir";
                    } else if (orientation === "-") {
                        classes += " leftdir";
                    } else {
                        throw new Error(
                            "Invalid node orientation " + orientation
                        );
                    }
                    scope.cy.add({
                        data: nodeData,
                        position: {
                            x: nodeVals[nodeAttrs.x],
                            y: nodeVals[nodeAttrs.y],
                        },
                        classes: classes,
                    });
                });
                _.each(dataHolder.getEdgesInComponent(sizeRank), function (
                    edge
                ) {
                    // TODO: replicate renderEdgeObject() here. Yeesh!
                });
            });
            this.finishDraw();
        }

        /**
         * Enables interaction with the graph interface after drawing.
         */
        finishDraw() {
            this.cy.endBatch();
            this.cy.fit();
            // Set minZoom to whatever the zoom level when viewing the entire drawn
            // component at once (i.e. right now) is, divided by 2 to give some
            // leeway for users to zoom out if they want
            this.cy.minZoom(this.cy.zoom() / 2);

            // Enable interaction with the graph
            this.cy.userPanningEnabled(true);
            this.cy.userZoomingEnabled(true);
            this.cy.boxSelectionEnabled(true);
            this.cy.autounselectify(false);
            this.cy.autoungrabify(false);
        }

        /**
         * Adjusts the size of the Cytoscape.js area.
         *
         * Should be called whenever the page dimensions are changed (i.e. the
         * control panel is hidden / un-hidden).
         */
        toggleSize() {
            this.cyDiv.toggleClass("nosubsume");
            this.cyDiv.toggleClass("subsume");
            if (!_.isNull(this.cy)) {
                this.cy.resize();
            }
        }
    }
    return { Drawer: Drawer };
});
