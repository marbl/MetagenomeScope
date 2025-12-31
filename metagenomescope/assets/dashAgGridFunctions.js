var dagfuncs = window.dashAgGridFunctions = window.dashAgGridFunctions || {};

// adapted from https://community.plotly.com/t/ag-grid-customized-sorting-order-in-column/77155/2
// see https://dash.plotly.com/dash-ag-grid/row-sorting#custom-sorting also

dagfuncs.compareFlyeApproxLengths = (valueA, valueB, nodeA, nodeB, isDescending) => {
    // Slice off the final "k": "1.8k" -> "1.8", etc.
    var lenA = parseFloat(valueA.substring(0, valueA.length - 1));
    var lenB = parseFloat(valueB.substring(0, valueB.length - 1));
    if (lenA == lenB) {
        return 0;
    } else {
        return (lenA > lenB) ? 1 : -1;
    }
}
