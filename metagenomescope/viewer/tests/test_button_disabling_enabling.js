mgsc.mochaTestSampleButtonClicked = false;
mgsc.mochaTestEmitSampleButtonClicked = function () {
    mgsc.mochaTestSampleButtonClicked = true;
};
mgsc.resetMochaTestSampleButton = function () {
    disableButton("mochaTestSampleButton");
    mgsc.mochaTestSampleButtonClicked = false;
};

describe("disableButton()", function () {
    mgsc.mochaTestSampleButtonClicked = false;
    it("Prevents a button from being clicked", function () {
        // Make sure our test environment is initially sane
        chai.assert.isFalse(mgsc.mochaTestSampleButtonClicked);
        // Call disableButton() then try to click it
        disableButton("mochaTestSampleButton");
        // It looks like calling .click() on a jQuery element bypasses the
        // element's disabled/enabled status, while the DOM element version
        // (returned by document.getElementById()) respects the
        // disabled/enabled status (thereby providing a better simulation of
        // what an actual mouse event is like).
        // CODELINK: Initial question in https://stackoverflow.com/q/6157929
        // (introduced me to the .click() method on raw DOM elements).
        document.getElementById("mochaTestSampleButton").click();
        // Make sure that we couldn't click the button
        chai.assert.isFalse(mgsc.mochaTestSampleButtonClicked);
        // Reset test environment
        mgsc.resetMochaTestSampleButton();
    });
    //it("Applies the disabled element/button CSS", function() {
    //    // Check that CSS attributes are kosher
    //});
    //it("Can be used multiple times without changing anything", function() {
    //    // Use it a bunch of times and check that it's still unclickable + CSS
    //    // is still good
    //});
});

describe("enableButton()", function () {
    it("Enables clicking a previously disabled button", function () {
        // Again: make sure our test environment is initially sane
        chai.assert.isFalse(mgsc.mochaTestSampleButtonClicked);
        // Call enableButton on the disabled button then try to click it
        enableButton("mochaTestSampleButton");
        document.getElementById("mochaTestSampleButton").click();
        // Make sure that we could click the button
        chai.assert.isTrue(mgsc.mochaTestSampleButtonClicked);
        // Reset test environment
        mgsc.resetMochaTestSampleButton();
    });
    //it("Applies the enabled element/button CSS", function() {
    //    // Check that CSS attributes are again kosher
    //});
    //it("Can be used multiple times without changing anything", function() {
    //    // Use it a bunch of times and check that it's still clickable + CSS
    //    // is still good
    //});
});
