mocha.setup("bdd");
mgsc.runTests = function () {
    mocha.run();
    // to make a long story short: things go wrong if you try to run tests more
    // than once without refreshing the browser, so we disable the runTests
    // button after running tests once
    disableButton("runTestsButton");
};
