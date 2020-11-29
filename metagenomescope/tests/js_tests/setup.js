/**
 * Adapted from
 * https://github.com/biocore/qurro/blob/master/qurro/support_files/main.js +
 * https://github.com/biocore/qurro/blob/master/qurro/tests/web_tests/setup.js.
 *
 * (And, to be fair, some of that code was initially adapted from the initial
 * tests I wrote for MetagenomeScope, so it's kind of a strange
 * self-perpetuating cycle of hacked-together test code written using coffee
 * and desperation. You could make a religion out of this.)
 */
requirejs.config({
    paths: {
        "app-manager": "instrumented_js/app-manager",
        "data-holder": "instrumented_js/data-holder",
        drawer: "instrumented_js/drawer",
        utils: "instrumented_js/utils",
        "dom-utils": "instrumented_js/dom-utils",
        jquery: "../../support_files/vendor/js/jquery-3.2.1.min",
        underscore: "../../support_files/vendor/js/underscore-min",
        bootstrap: "../../support_files/vendor/js/bootstrap.min",
        cytoscape: "../../support_files/vendor/js/cytoscape.min",
        "bootstrap-colorpicker":
            "../../support_files/vendor/js/bootstrap-colorpicker.min",
        mocha: "vendor/mocha",
        chai: "vendor/chai",
    },
    shim: {
        bootstrap: { deps: ["jquery"] },
        "bootstrap-colorpicker": { deps: ["bootstrap", "jquery"] },
        // Mocha shim based on
        // https://gist.github.com/michaelcox/3800736#gistcomment-1417093.
        mocha: {
            init: function () {
                mocha.setup("bdd");
                return mocha;
            },
        },
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
        "mocha",
        "chai",
        "test_distances",
    ],
    function (
        AppManager,
        DataHolder,
        Drawer,
        Utils,
        DomUtils,
        $,
        _,
        bootstrap,
        bootstrapColorpicker,
        cy,
        mocha,
        chai,
        test_distances
    ) {
        mocha.checkLeaks();
        mocha.run();
    }
);
