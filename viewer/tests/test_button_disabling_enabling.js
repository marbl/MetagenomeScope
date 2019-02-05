// TODO for this: basically just load the entire HTML page as an iframe, then
// mess with its elements (cy, etc) normally.
describe("disableButton()", function() {
    it("Prevents a button from being clicked", function() {
        // Call disableButton() then try to click it via mouse and .click()
    });
    it("Applies the disabled element/button CSS", function() {
        // Check that CSS attributes are kosher
    });
    it("Can be used multiple times without changing anything", function() {
        // Use it a bunch of times and check that it's still unclickable + CSS
        // is still good
    });
});

describe("enableButton()", function() {
    it("Enables interaction with a disabled button", function() {
        // Call enableButton on the disabled button then try to click it
        // via mouse and .click()
    });
    it("Applies the enabled element/button CSS", function() {
        // Check that CSS attributes are again kosher
    });
    it("Can be used multiple times without changing anything", function() {
        // Use it a bunch of times and check that it's still clickable + CSS
        // is still good
    });
});
