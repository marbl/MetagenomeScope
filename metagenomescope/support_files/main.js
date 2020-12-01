/**
 * Adapted from
 * https://github.com/biocore/qurro/blob/master/qurro/support_files/main.js.
 */
requirejs.config({
    baseUrl: "js",
    paths: {
        jquery: "../vendor/js/jquery-3.2.1.min",
        underscore: "../vendor/js/underscore-min",
        bootstrap: "../vendor/js/bootstrap.min",
        cytoscape: "../vendor/js/cytoscape.min",
        "cytoscape-expand-collapse": "../vendor/js/cytoscape-expand-collapse",
        "bootstrap-colorpicker": "../vendor/js/bootstrap-colorpicker.min",
    },
    shim: {
        bootstrap: { deps: ["jquery"] },
        "bootstrap-colorpicker": { deps: ["bootstrap", "jquery"] },
    },
});
requirejs(
    [
        "app-manager",
        "data-holder",
        "drawer",
        "utils",
        "dom-utils",
        "jquery",
        "underscore",
        "bootstrap",
        "bootstrap-colorpicker",
        "cytoscape",
        "cytoscape-expand-collapse",
    ],
    function (AppManager, DataHolder, Drawer, Utils, DomUtils, $, _, bootstrap, bootstrapColorpicker, cy, cyEC) {
        // Get the graph data JSON from the preprocessing script.
        var dataJSON = {{ dataJSON }};
        var dh = new DataHolder.DataHolder(dataJSON);
        new AppManager.AppManager(dh);
    }
);
