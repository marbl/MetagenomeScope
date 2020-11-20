define(["jquery", "underscore", "cytoscape"], function ($, _, cy) {
    class Drawer {
        constructor(cyDiv) {
            this.cyDiv = $("#" + cyDiv);
            // Instance of Cytoscape.js
            this.cy = null;
        }

        draw(nodes, edges, patterns) {}

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
