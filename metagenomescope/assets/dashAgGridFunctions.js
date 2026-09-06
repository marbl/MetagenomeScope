// https://dash.plotly.com/dash-ag-grid/row-sorting#custom-sorting
var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});

/* Formats a list of connected component numbers to be comma-separated. */
dagfuncs.numListValueFormatter = function (c) {
    return c.join(", ");
};

/* Compares two sorted lists of connected component numbers.
 *
 * @param {Array} c1 First such list.
 * @param {Array} c2 Second such list.
 * @return {Number} 0, -1, or 1: c1 === c2, c1 < c2, or c1 > c2 respectively
 */
dagfuncs.numListComparator = function (c1, c2) {
    var i = 0;
    while (true) {
        if (i < c1.length) {
            if (i < c2.length) {
                if (c1[i] !== c2[i]) {
                    if (c1[i] < c2[i]) {
                        return -1;
                    } else {
                        return 1;
                    }
                }
                // making it here means that c1[i] === c2[i], so keep looking
            } else {
                // c1 has more stuff in it than c2
                return 1;
            }
        } else {
            if (i < c2.length) {
                // c2 has more stuff in it than c1
                return -1;
            } else {
                // c1 and c2 have the same length, and we haven't seen any
                // differences between them, so they are equal
                return 0;
            }
        }
        i++;
    }
    // Should never get here
    throw new Error(
        "sorting cc arrays broke: " + c1.toString() + " & " + c2.toString(),
    );
};
