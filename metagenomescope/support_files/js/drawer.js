define(["jquery", "underscore", "cytoscape"], function ($, _, cy) {
    class Drawer {
        constructor(cyDiv) {
            this.cyDiv = $("#" + cyDiv);
            // Instance of Cytoscape.js
            this.cy = null;
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
         *                 respect to the dataHolder.
         */
        draw(componentsToDraw, dataHolder) {
            this.validateComponentRanks(componentsToDraw);
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
