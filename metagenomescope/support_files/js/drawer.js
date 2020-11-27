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
                            "z-index-compare": "manual",
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

        renderPattern(pattAttrs, pattVals, pattID, dx, dy) {
            var pattData = {
                id: pattID,
                w: pattVals[pattAttrs.width],
                h: pattVals[pattAttrs.height],
                isCollapsed: false,
            };
            var classes = "pattern";
            if (pattVals[pattAttrs.pattern_type] === "chain") {
                classes += " C";
            } else if (pattVals[pattAttrs.pattern_type] === "cyclicchain") {
                classes += " Y";
            } else if (pattVals[pattAttrs.pattern_type] === "bubble") {
                classes += " B";
            } else if (pattVals[pattAttrs.pattern_type] === "frayedrope") {
                classes += " F";
            } else {
                classes += " M";
            }
            var x =
                dx + (pattVals[pattAttrs.left] + pattVals[pattAttrs.right]) / 2;
            var y =
                dy + (pattVals[pattAttrs.bottom] + pattVals[pattAttrs.top]) / 2;
            this.cy.add({
                data: pattData,
                position: { x: x, y: y },
                classes: classes,
            });
            console.log(
                "Rendered pattern " + pattID + " at (" + x + ", " + y + ")"
            );
        }

        renderNode(nodeAttrs, nodeVals, nodeID, dx, dy) {
            var nodeData = {
                id: nodeID,
                label: nodeVals[nodeAttrs.name],
                length: nodeVals[nodeAttrs.length],
                w: nodeVals[nodeAttrs.width],
                h: nodeVals[nodeAttrs.height],
            };
            var classes = "basic";
            var orientation = nodeVals[nodeAttrs.orientation];
            if (orientation === "+") {
                classes += " rightdir";
            } else if (orientation === "-") {
                classes += " leftdir";
            } else {
                throw new Error("Invalid node orientation " + orientation);
            }
            var x = nodeVals[nodeAttrs.x] + dx;
            var y = nodeVals[nodeAttrs.y] + dy;
            this.cy.add({
                data: nodeData,
                position: { x: x, y: y },
                classes: classes,
            });
            console.log(
                "Rendered node " +
                    nodeID +
                    " (name " +
                    nodeVals[nodeAttrs.name] +
                    ") at (" +
                    x +
                    ", " +
                    y +
                    ")"
            );
        }

        renderEdge(edgeAttrs, edgeVals, srcID, snkID) {
            var MIN_EDGE_THICKNESS = 3;
            var MAX_EDGE_THICKNESS = 10;
            var EDGE_THICKNESS_RANGE = MAX_EDGE_THICKNESS - MIN_EDGE_THICKNESS;
            var edgeWidth =
                MIN_EDGE_THICKNESS +
                edgeVals[edgeAttrs.relative_weight] * EDGE_THICKNESS_RANGE;
            var classes = "oriented";
            if (edgeVals[edgeAttrs.is_outlier] === 1) {
                classes += " high_outlier";
            } else if (edgeVals[edgeAttrs.is_outlier] === -1) {
                classes += " low_outlier";
            }
            if (srcID === snkID) {
                // It's a self-directed edge; don't bother parsing ctrl pt
                // info, just render it as a bezier edge and be done with it
                this.cy.add({
                    classes: classes + " basicbezier",
                    data: {
                        source: srcID,
                        target: snkID,
                        thickness: edgeWidth,
                    },
                });
                return;
            } else {
                // TODO: Get the positions of the source and sink node
                // (probs just pass it directly into renderEdge() -- get it
                // from the data holder directly in draw()). Convert into
                // distances and weights for each point, which we can set as
                // the cpd / cpw data attributes of an edge. If the control
                // points basically approximate a straight line between source
                // and sink then we can just draw a basicbezier instead.
                //
                // For now we just draw a straight line in any case
                this.cy.add({
                    classes: classes + " basicbezier",
                    data: {
                        source: srcID,
                        target: snkID,
                        thickness: edgeWidth,
                    },
                });
            }
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
            // TODO: set graph bindings
            this.cy.startBatch();
            // These are the "offsets" from the top-left of each component's
            // bounding box, used when drawing multiple components at once.
            var maxWidth = null;
            var dx = 0;
            var dy = 0;
            _.each(componentsToDraw, function (sizeRank) {
                var pattAttrs = dataHolder.getPattAttrs();
                _.each(dataHolder.getPatternsInComponent(sizeRank), function (
                    pattVals,
                    pattID
                ) {
                    scope.renderPattern(pattAttrs, pattVals, pattID, dx, dy);
                });
                var nodeAttrs = dataHolder.getNodeAttrs();
                _.each(dataHolder.getNodesInComponent(sizeRank), function (
                    nodeVals,
                    nodeID
                ) {
                    scope.renderNode(nodeAttrs, nodeVals, nodeID, dx, dy);
                });
                var edgeAttrs = dataHolder.getEdgeAttrs();
                // Edges are a bit different: they're structured as
                // {srcID: {snkID: edgeVals, snkID2: edgeVals}, ...}
                _.each(dataHolder.getEdgesInComponent(sizeRank), function (
                    edgesFromSrcID,
                    srcID
                ) {
                    _.each(edgesFromSrcID, function (edgeVals, snkID) {
                        scope.renderEdge(
                            edgeAttrs,
                            edgeVals,
                            srcID,
                            snkID,
                            dx,
                            dy
                        );
                    });
                });
                var componentBoundingBox = dataHolder.getComponentBoundingBox(
                    sizeRank
                );
                dy += componentBoundingBox[1];
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

        /**
         * Fits the graph: either to all elements or just to those selected.
         *
         * @param {Boolean} toSelected If true, fit to just the currently-
         *                             selected elements in the graph; if
         *                             false, fit to all drawn elements.
         */
        fit(toSelected) {
            // TODO: use progress bar
            if (toSelected) {
                // Right now, we don't throw any sort of error here if
                // no elements are selected. This is because the fit-selected
                // button should only be enabled when >= 1 elements are
                // selected.
                this.cy.fit(cy.$(":selected"));
            } else {
                this.cy.fit();
            }
        }
    }
    return { Drawer: Drawer };
});
