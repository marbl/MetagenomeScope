define(["jquery", "cytoscape", "utils", "dom-utils"], function (
    $,
    cy,
    utils,
    domUtils
) {
    class AppManager {
        constructor(dataHolder) {
            // Holds all of the actual graph data (nodes, edges, etc.)
            this.dataHolder = dataHolder;

            this.numComponents = this.dataHolder.numComponents();

            // Instance of Cytoscape.js used to draw the graph.
            this.cy = null;

            this.controlsDiv = $("#controls");
            this.cyDiv = $("#cy");

            $(this.doThingsWhenDOMReady.bind(this));

            // Set the component selection method to whatever the first thing
            // in the component selection method dropdown menu is
            this.cmpSelectionMethod = $("#cmpSelectionMethod").val();
        }

        /**
         * Set various bindings, enable elements that don't need to have
         * something drawn on the screen, etc.
         */
        doThingsWhenDOMReady() {
            // Make that "hamburger" button show/hide the control panel
            $("#controlsToggler").click(this.toggleControls.bind(this));

            // Make the "Graph info" button show a modal dialog
            $("#infoButton").click(function () {
                $("#infoDialog").modal();
            });
            domUtils.enableButton("infoButton");

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
            $("#decrCompRankButton").click(domUtils.decrCompRank);
            $("#incrCompRankButton").click(domUtils.incrCompRank);
            $("#drawButton").click(this.draw.bind(this));

            // On a new component selection method being, well, selected,
            // update this.cmpSelectionMethod.
            $("#cmpSelectionMethod").change(this.updateCmpSelectionMethod.bind(this));

            domUtils.enablePersistentControls(this.numComponents);

            this.populateGraphInfoMain();
            // TODO: Set up node / edge / pattern info tables -- take into
            // account optional stuff like coverage, GC content, multiplicity,
            // ...
        }

        /**
         * Toggles whether or not the controls div is shown, adjusting the
         * size of the Cytoscape.js div if applicable.
         */
        toggleControls() {
            this.controlsDiv.toggleClass("notviewable");
            this.cyDiv.toggleClass("nosubsume");
            this.cyDiv.toggleClass("subsume");
            if (this.cy !== null) {
                this.cy.resize();
            }
        }

        /**
         * Updates the component selection method (e.g. "draw just a single
         * component", "draw all components", etc.) based on the option that
         * was selected.
         *
         * @param {Event} eve The event sent about the click event.
         */
        updateCmpSelectionMethod(e) {
            this.cmpSelectionMethod = e.target.value;
        }

        populateGraphInfoMain() {
            // TODO: populate with basic graph-level stuff. mention no component drawn yet.
        }

        populateGraphInfoCurrComponents() {
            // TODO: populate based on the component(s) currently drawn.
        }

        initGraph() {
            // TODO: init cytoscape, etc
        }

        /**
         * Returns an array containing all of the components to draw.
         *
         * If the components to draw are invalid in some way (e.g. they refer
         * to a component or a node that does not exist), this will open an
         * alert message (letting the user know what happened) and throw an
         * error (stopping execution of draw()).
         */
        getComponentsToDraw() {
            // TODO: Check status of component drawing select and then use that
            // to inform which UI elements are checked.
            return [];
        }

        draw() {
            var componentsToDraw = this.getComponentsToDraw();
            console.log("Drawing components " + componentsToDraw);
            // TODO: (This is just replicating drawComponent().)
            // -disable volatile controls
            // -if cy !== null, destroy graph
            // -set graph bindings
            // -load data from the data holder and populate things
            //  (Maybe pass cy to this.dataHolder and have it do that there?)
            // -Patterns
            // -Nodes
            // -Edges
            // -Set up interface
        }
    }
    return { AppManager: AppManager };
});
