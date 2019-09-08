describe("distance()", function() {
    it("Computes distance between two [x, y] points", function() {
        chai.assert.equal(distance([1, 2], [3, 4]), Math.sqrt(8));
    });
    it("Returns 0 when the two points are the same", function() {
        chai.assert.equal(distance([-1, -5], [-1, -5]), 0);
    });
    it("Can handle large-ish distances (i.e. results on the order of 1 million)", function() {
        chai.assert.approximately(
            distance([0, 0], [-12345, 10000000]),
            // generated by python3 via sqrt(12345**2 + 10000000**2)
            10000007.619948346,
            0.001 // "delta" value
        );
    });
});