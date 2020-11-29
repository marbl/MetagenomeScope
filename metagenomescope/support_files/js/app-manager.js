define(["jquery", "underscore", "drawer", "utils", "dom-utils"], function (
    $,
    _,
    Drawer,
    Utils,
    DomUtils
) {
    class AppManager {
        constructor(dataHolder) {
            // Holds all of the actual graph data (nodes, edges, etc.)
            this.dataHolder = dataHolder;

            this.numComponents = this.dataHolder.numComponents();

            // Set up the Drawer, which'll interface with Cytoscape.js.
            // We pass a few callbacks to the Drawer so that the Drawer can let
            // the App Manager know when various things happen in the graph.
            this.drawer = new Drawer.Drawer(
                "cy",
                this.onSelect.bind(this),
                this.onUnselect.bind(this),
                this.onTogglePatternCollapse.bind(this)
            );

            this.controlsDiv = $("#controls");

            $(this.doThingsWhenDOMReady.bind(this));

            this.cmpSelectionMethod = undefined;
            // Set the component selection method to whatever the
            // currently-selected value in the component selection method
            // dropdown menu is, and sort out the UI accordingly
            this.updateCmpSelectionMethod();
        }

        /**
         * Set various bindings, enable elements that don't need to have
         * something drawn on the screen, etc.
         */
        doThingsWhenDOMReady() {
            var scope = this;
            // Make that "hamburger" button show/hide the control panel
            $("#controlsToggler").click(this.toggleControls.bind(this));

            // Make the "Graph info" button show a modal dialog
            $("#infoButton").click(function () {
                $("#infoDialog").modal();
            });
            DomUtils.enableButton("infoButton");

            // Make the "Settings" button show the settings dialog
            $("#settingsButton").click(function () {
                $("#settingsDialog").modal();
            });

            // Pop open the wiki when the help button is clicked
            $("#helpButton").click(function () {
                window.open(
                    "https://github.com/marbl/MetagenomeScope/wiki",
                    "_blank"
                );
            });

            // Set up the component selector
            var svc = this.dataHolder.smallestViewableComponent();
            $("#componentselector").prop("value", svc);
            // Setting the min to 1 instead of svc is done for a few reasons:
            // 1. No guarantee that the maximum-number component will also be
            //    drawable (although that should probably never happen in
            //    practice, because usually there are a lot of components with
            //    just 1 node) -- so we should be consistent.
            // 2. Shows the user that components are 1-indexed, so the largest
            //    component is #1.
            $("#componentselector").prop("min", 1);
            $("#componentselector").prop("max", this.numComponents);
            $("#decrCompRankButton").click(DomUtils.decrCompRank);
            $("#incrCompRankButton").click(DomUtils.incrCompRank);
            $("#drawButton").click(this.draw.bind(this));

            // On a new component selection method being, well, selected,
            // update this.cmpSelectionMethod.
            $("#cmpSelectionMethod").change(
                this.updateCmpSelectionMethod.bind(this)
            );

            DomUtils.enablePersistentControls(this.numComponents);

            this.populateGraphInfoMain();

            _.each(["node", "edge", "pattern"], function (eleType) {
                $("#" + eleType + "Header").click(function () {
                    scope.toggleEleInfo(eleType);
                });
            });
            // TODO: Set up node / edge / pattern info tables -- take into
            // account optional stuff like coverage, GC content, multiplicity,
            // ...

            // Set up colorpickers
            $(".colorpicker-component").colorpicker({ format: "hex" });

            // Set up "fit" buttons
            $("#fitButton").click(function () {
                scope.drawer.fit(false);
            });
            $("#fitSelectedButton").click(function () {
                scope.drawer.fit(true);
            });
        }

        /**
         * Toggles whether or not the controls div is shown, adjusting the
         * size of the Cytoscape.js div if applicable.
         */
        toggleControls() {
            this.controlsDiv.toggleClass("notviewable");
            this.drawer.toggleSize();
        }

        /**
         * Toggles a "Selected Element" section of the control panel.
         *
         * There are three of these sections -- nodes, edges, and patterns.
         *
         * @param {String} eleType One of "node", "edge", "pattern".
         *
         * @throws {Error} if eleType is invalid
         */
        toggleEleInfo(eleType) {
            var validEleTypes = ["node", "edge", "pattern"];
            if (_.contains(validEleTypes, eleType)) {
                var openerID = "#" + eleType + "Opener";
                var infoDivID = "#" + eleType + "Info";
                if ($(openerID).hasClass("glyphicon-triangle-right")) {
                    $(openerID).removeClass("glyphicon-triangle-right");
                    $(openerID).addClass("glyphicon-triangle-bottom");
                } else {
                    $(openerID).removeClass("glyphicon-triangle-bottom");
                    $(openerID).addClass("glyphicon-triangle-right");
                }
                $(infoDivID).toggleClass("notviewable");
            } else {
                throw new Error("Unrecognized eleType: " + eleType);
            }
        }

        /**
         * Updates the component selection method (e.g. "draw just a single
         * component", "draw all components", etc.) based on the option that
         * is currently selected, and shows/hides certain UI elements within
         * the "Drawing" control panel section accordingly.
         *
         * By hiding all UI elements, rather than trying to maintain a record
         * of whatever the previously-selected method was (if any was
         * selected), we can get around some corner cases -- see the HTML
         * for some details. There are only, like, three of these options
         * anyway, so this shouldn't be a performance problem.
         */
        updateCmpSelectionMethod() {
            var newMethod = $("#cmpSelectionMethod").val();
            $("#cmpSelectionMethod")
                .children()
                .each(function (i, e) {
                    if (e.value !== newMethod) {
                        // Hide other selection UIs
                        $("#" + e.value + "-draw-eles").addClass("notviewable");
                    } else {
                        // Show the now-selected component selection UI
                        $("#" + newMethod + "-draw-eles").removeClass(
                            "notviewable"
                        );
                    }
                });
            this.cmpSelectionMethod = newMethod;
        }

        /**
         * Populates the "graph information" table based on the data holder.
         *
         * This should only be called once; the information applied here should
         * not change as the graph is drawn.
         */
        populateGraphInfoMain() {
            $("#filenameEntry").text(this.dataHolder.fileName());
            $("#filetypeEntry").text(this.dataHolder.fileType());
            $("#nodeCtEntry").text(this.dataHolder.totalNumNodes());
            $("#edgeCtEntry").text(this.dataHolder.totalNumEdges());
            $("#ccCtEntry").text(this.dataHolder.numComponents());
        }

        populateGraphInfoCurrComponents() {
            // TODO: populate based on the component(s) currently drawn.
        }

        /**
         * Returns an array containing all of the components to draw.
         *
         * If the components to draw are invalid in some way (e.g. they refer
         * to a component or a node that does not exist), this will open an
         * alert message (letting the user know what happened) and throw an
         * error (stopping execution of draw()).
         *
         * @returns {Array} Size ranks (1-indexed) of the component(s) to draw,
         *                  stored as Numbers. This will be an Array no matter
         *                  what, so even if just one component will be drawn
         *                  this'll still return an Array with just that one
         *                  Number.
         *
         * @throws {Error} If component selection is invalid (e.g. the size
         *                 rank is out of range for method === "single", or the
         *                 node name for method === "withnode" is not in the
         *                 graph)
         */
        getComponentsToDraw() {
            if (this.cmpSelectionMethod === "single") {
                var cmpRank = $("#componentselector").val();
                if (DomUtils.compRankValidity(cmpRank) !== 0) {
                    // TODO? -- give more detailed error messages listing e.g.
                    // the lowest laid out component rank
                    alert("Please enter a valid component size rank.");
                    throw new Error("Invalid component size rank.");
                } else {
                    return [parseInt(cmpRank)];
                }
            } else if (this.cmpSelectionMethod === "withnode") {
                var name = $("#nodeNameSelector").val();
                var cmpRank = this.dataHolder.findComponentContainingNodeName(
                    name
                );
                if (cmpRank === -1) {
                    alert(
                        'No laid-out components contain a node with the name "' +
                            name +
                            '".'
                    );
                    throw new Error("Invalid node name.");
                } else {
                    return [cmpRank];
                }
            } else if (this.cmpSelectionMethod === "all") {
                return this.dataHolder.getAllLaidOutComponentRanks();
            } else {
                throw new Error(
                    "Invalid cmp selection method set: " +
                        this.cmpSelectionMethod
                );
            }
        }

        /**
         * Updates the selected elements section in response to an element
         * being selected.
         *
         * @param {Cytoscape.js Event} eve Event triggered by Cytoscape.js.
         */
        onSelect(eve) {
            var x = eve.target;
            if (x.hasClass("node")) {
                if (x.hasClass("basic")) {
                    // It's a regular node (not a pattern).
                } else {
                    // It's a pattern.
                }
            } else {
                // It's an edge.
            }
        }

        /**
         * Updates the selected elements section in response to an element
         * being unselected.
         *
         * @param {Cytoscape.js Event} eve Event triggered by Cytoscape.js.
         */
        onUnselect(eve) {
            var x = eve.target;
            console.log(x.data());
            if (x.hasClass("node")) {
                if (x.hasClass("basic")) {
                    // It's a regular node (not a pattern).
                } else {
                    // It's a pattern.
                }
            } else {
                // It's an edge.
            }
        }

        /**
         * Collapses/uncollapses a pattern.
         *
         * @param {Cytoscape.js Event} eve Event triggered by Cytoscape.js.
         */
        onTogglePatternCollapse(eve) {
            var x = eve.target;
        }

        /**
         * Attempts to draw component(s) based on the component(s) selected.
         *
         * It's very possible that this.getComponentsToDraw() will fail if the
         * current component selection is invalid (e.g. an invalid size rank is
         * selected). In that case, this.getComponentsToDraw() will just throw
         * an Error, and this'll stop before it actually calls
         * this.drawer.draw().
         *
         * @throws {Error} If component selection is invalid.
         */
        draw() {
            var componentsToDraw = this.getComponentsToDraw();
            this.drawer.draw(componentsToDraw, this.dataHolder);
            // Enable controls that only have meaning when stuff is drawn (e.g.
            // the "fit graph" buttons)
            DomUtils.enableDrawNeededControls();
        }
    }
    return { AppManager: AppManager };
});
