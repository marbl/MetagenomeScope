// These tests should only be run after a graph has been loaded, since they
// (and the functions they call) rely on mgsc.CURR_ROTATION and PREV_ROTATION
// having already been set.
describe("Graph Rotation", function() {
    it("Current graph rotation should be 90 degrees", function() {
        chai.assert.equal(mgsc.CURR_ROTATION, 90);
    });
    it('"Previous" graph rotation should be 0 degrees', function() {
        chai.assert.equal(mgsc.PREV_ROTATION, 0);
    });
});
describe("getNodeCoordClass()", function() {
    it('Should return "leftdir" for reverse-oriented contigs', function() {
        // That is, contigs that are marked with the "house" shape for dot
        chai.assert.equal(getNodeCoordClass(true), "leftdir");
    });
    it('Should return "rightdir" for forward-oriented contigs', function() {
        // That is, contigs that are marked with the "invhouse" shape for dot
        chai.assert.equal(getNodeCoordClass(false), "rightdir");
    });
});
// TODO: test getClusterCoordClass(), gv2cyPoint, ctrlPtStrToList, etc.
