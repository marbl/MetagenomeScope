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
        var dataJSON = {"node_attrs": {"name": 0, "length": 1, "x": 2, "y": 3, "width": 4, "height": 5, "orientation": 6, "parent_id": 7, "is_dup": 8}, "edge_attrs": {"ctrl_pt_coords": 0, "is_outlier": 1, "relative_weight": 2, "is_dup": 3, "parent_id": 4, "bsize": 5, "orientation": 6, "mean": 7, "stdev": 8}, "patt_attrs": {"pattern_id": 0, "left": 1, "bottom": 2, "right": 3, "top": 4, "width": 5, "height": 6, "pattern_type": 7, "parent_id": 8}, "extra_node_attrs": [], "extra_edge_attrs": ["bsize", "orientation", "mean", "stdev"], "components": [{"nodes": {"0": ["NODE_10", 100, -1993.5, 500.75, 196.2979100576472, 111.205972562771, "+", 14, false], "7": ["NODE_11", 100, -252.5, 500.75, 196.2979100576472, 111.205972562771, "+", 14, false], "1": ["NODE_1", 100, -1383.0, 295.75, 196.2979100576472, 111.205972562771, "+", 12, false], "3": ["NODE_2", 100, -1123.0, 150.75, 196.2979100576472, 111.205972562771, "+", 12, false], "4": ["NODE_3", 100, -1123.0, 295.75, 196.2979100576472, 111.205972562771, "-", 12, false], "5": ["NODE_4", 100, -1123.0, 440.75, 196.2979100576472, 111.205972562771, "+", 12, false], "6": ["NODE_5", 100, -863.0, 295.75, 196.2979100576472, 111.205972562771, "+", 12, false], "2": ["NODE_6", 100, -1643.0, 754.385, 196.2979100576472, 111.205972562771, "+", 13, false], "8": ["NODE_7", 100, -1383.0, 708.385, 196.2979100576472, 111.205972562771, "+", 13, false], "10": ["NODE_8", 100, -863.0, 708.385, 196.2979100576472, 111.205972562771, "+", 13, false], "9": ["NODE_12", 100, -1123.0, 708.385, 196.2979100576472, 111.205972562771, "+", 13, false], "11": ["NODE_9", 100, -603.0, 662.384, 196.2979100576472, 111.205972562771, "+", 13, false]}, "edges": {"0": {"1": [[-1881.5, 500.75, -1711.5, 500.75, -1722.1, 304.07, -1559.4, 296.01], 0, 0.5, false, 14, 30, "EB", "-200.00", 25.1234], "2": [[-1881.5, 500.75, -1792.4, 500.75, -1926.6, 690.2, -1855.7, 705.74], 0, 0.5, false, 14, 30, "EB", "-200.00", 25.1234]}, "6": {"7": [[-697.0, 295.75, -519.22, 295.75, -525.4200000000001, 493.02, -354.65, 500.53], 0, 0.5, false, 14, 30, "EB", "-200.00", 25.1234]}, "11": {"7": [[-400.5, 706.75, -309.33000000000004, 706.75, -429.28, 516.53, -354.6, 501.67], 0, 0.5, false, 14, 30, "EB", "-200.00", 25.1234]}, "1": {"3": [[-1271.0, 295.75, -1205.69, 295.75, -1275.55, 166.176, -1225.03, 152.00400000000002], 0, 0.5, false, 12, 30, "EB", "-200.00", 25.1234], "4": [[-1271.0, 295.75, -1259.0, 295.75, -1253.75, 295.75, -1245.12, 295.75], 0, 0.5, false, 12, 30, "EE", "-200.00", 25.1234], "5": [[-1271.0, 295.75, -1205.69, 295.75, -1275.55, 425.32, -1225.03, 439.5], 0, 0.5, false, 12, 30, "EB", "-200.00", 25.1234]}, "3": {"6": [[-1011.0, 150.75, -945.69, 150.75, -1015.55, 280.32, -965.03, 294.5], 0, 0.5, false, 12, 30, "EB", "-200.00", 25.1234]}, "4": {"6": [[-1031.0, 295.75, -1000.92, 295.75, -990.9300000000001, 295.75, -965.24, 295.75], 0, 0.5, false, 12, 30, "BB", "-200.00", 25.1234]}, "5": {"6": [[-1011.0, 440.75, -945.69, 440.75, -1015.55, 311.18, -965.03, 297.0], 0, 0.5, false, 12, 30, "EB", "-200.00", 25.1234]}, "2": {"8": [[-1531.0, 754.385, -1502.7, 754.385, -1505.8, 718.845, -1485.06, 710.245], 0, 0.5, false, 13, 30, "EB", "-200.00", 25.1234], "10": [[-1531.0, 754.385, -1511.3, 754.385, -1513.8, 774.315, -1495.0, 780.385, -1290.3200000000002, 846.565, -1204.24, 874.895, -1011.0, 780.385, -978.14, 764.315, -991.99, 718.625, -965.23, 709.845], 0, 0.5, false, 13, 30, "EB", "-200.00", 25.1234]}, "8": {"9": [[-1271.0, 708.385, -1250.0, 708.385, -1242.29, 708.385, -1225.44, 708.385], 0, 0.5, false, 13, 30, "EB", "-200.00", 25.1234], "11": [[-1271.0, 708.385, -1234.8200000000002, 708.385, -1265.72, 654.486, -1235.0, 635.384, -1052.33, 521.791, -960.71, 587.4680000000001, -751.0, 635.384, -727.75, 640.697, -723.5, 656.9580000000001, -705.0, 661.3050000000001], 0, 0.5, false, 13, 30, "EB", "-200.00", 25.1234]}, "9": {"10": [[-1011.0, 708.385, -990.0, 708.385, -982.29, 708.385, -965.44, 708.385], 0, 0.5, false, 13, 30, "EB", "-200.00", 25.1234]}, "10": {"11": [[-751.0, 708.385, -722.69, 708.385, -725.77, 672.845, -705.06, 664.244], 0, 0.5, false, 13, 30, "EB", "-200.00", 25.1234]}}, "patts": [[14, -2105.5, -57.25, -140.5, -860.75, 1965.0, 803.5, "bubble", null], [12, -1495.0, -87.25, -751.0, -504.25, 744.0, 417.0, "bubble", 14], [13, -1755.0, -571.975, -491.0, -841.525, 1264.0, 269.55, "bubble", 14]], "bb": [2246.0, 918.0], "skipped": false}], "input_file_basename": "marygold_fig2a.gml", "input_file_type": "gml", "total_num_nodes": 12, "total_num_edges": 16};
        var dh = new DataHolder.DataHolder(dataJSON);
        new AppManager.AppManager(dh);
    }
);