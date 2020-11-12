define(["jquery", "cytoscape", "util"], function ($, cy, util) {
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
