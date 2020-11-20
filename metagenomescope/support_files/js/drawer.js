define(["jquery", "underscore", "cytoscape"], function ($, _, cy) {
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
                layout: { name: "present" },
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
                        selector:
                            "node.pattern[?isCollapsed]",
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
                            "shape-polygon-points": "-1 -1 0 -0.5 1 -1 1 1 0 0.5 -1 1",
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
                            "shape-polygon-points": "-1 0 -0.5 -1 0.5 -1 1 0 0.5 1 -0.5 1",
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
                        selector: "node.cluster.pseudoparent",
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
                        selector: "node.noncluster",
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
                        selector: "node.noncluster.noncolorized",
                        style: {
                            "background-color": mgsc.DEFAULT_NODE_COLOR,
                            color: $("#usnlcp").colorpicker("getValue"),
                        },
                    },
                    // TODO: add a generalized "colorized" class or something
                    // for coloring by GC content, coverage, ...
                    {
                        selector: "node.noncluster.leftdir",
                        style: {
                            // Represents a node pointing left (i.e. in the
                            // reverse direction, if the graph flows from left
                            // to right)
                            //  ___
                            // /   |
                            // \___|
                            shape: "polygon",
                            "shape-polygon-points": "1 1 -0.23587 1 -1 0 -0.23587 -1 1 -1",
                        },
                    },
                    {
                        selector: "node.noncluster.rightdir",
                        style: {
                            // Represents a node pointing left (i.e. in the
                            // reverse direction, if the graph flows from left
                            // to right)
                            //  ___
                            // |   \
                            // |___/
                            shape: "polygon",
                            "shape-polygon-points": "-1 1 0.23587 1 1 0 0.23587 -1 -1 -1",
                        },
                    },
                    {
                        selector: "node.noncluster.tentative",
                        style: {
                            "border-width": 5,
                            "border-color": $("#tnbcp").colorpicker("getValue"),
                        },
                    },
                    // TODO pick up from here
                    // and rename noncluster to just nonpattern or something
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
                        selector: "node.noncluster:selected",
                        style: {
                            "background-color": $("#sncp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.noncluster.noncolorized:selected",
                        style: {
                            color: $("#snlcp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.noncluster.gccolorized:selected",
                        style: {
                            color: $("#csnlcp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.cluster:selected",
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
                    {
                        // Used to differentiate edges without an overlap between nodes
                        // in graphs where overlap data is given
                        // this conflicts with virtual edges' style, so we may want to
                        // change this in the future
                        // (using "dotted" lines was really slow)
                        selector: "edge.nooverlap",
                        style: {
                            "line-style": "dashed",
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
         *                 a dataholder method?)
         */
        draw(componentsToDraw, dataHolder) {
            if (!_.isNull(this.cy)) {
                this.destroyGraph();
            }
            this.initGraph();
            // set graph bindings
            // load data from the data holder and populate:
            // -patterns
            // -nodes
            // -edges
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
