define(["jquery", "bootstrap", "cytoscape", "util"], function (
    $,
    bootstrap,
    cy,
    util
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

        doThingsWhenDOMReady() {
            console.log(
                "This is a " +
                    this.dataHolder.fileType() +
                    " file named " +
                    this.dataHolder.fileName() +
                    " with " +
                    this.dataHolder.numComponents() +
                    " components."
            );
            $("#controlsToggler").click(this.toggleControls.bind(this));
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
