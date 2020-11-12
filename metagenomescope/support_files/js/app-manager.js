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

            // Instance of Cytoscape.js used to draw the graph.
            this.cy = null;

            this.controlsDiv = $("#controls");
            this.cyDiv = $("#cy");

            $(this.doThingsWhenDOMReady.bind(this));
        }

        /**
         * Set various bindings, etc.
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
                window.open("https://github.com/marbl/MetagenomeScope/wiki", "_blank");
            });
        }

        toggleControls() {
            this.controlsDiv.toggleClass("notviewable");
            this.cyDiv.toggleClass("nosubsume");
            this.cyDiv.toggleClass("subsume");
            if (this.cy !== null) {
                this.cy.resize();
            }
        }

        initGraph() {
            // TODO init cytoscape, etc
        }
    }
    return { AppManager: AppManager };
});
