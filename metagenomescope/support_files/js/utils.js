/* Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
 * Authored by Marcus Fedarko
 *
 * This file is part of MetagenomeScope.
 *
 * MetagenomeScope is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * MetagenomeScope is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
 ****
 * Various utilities used by MetagenomeScope.
 */
define(["underscore"], function (_) {
    /* Returns a #RRGGBB string indicating the color of a node, scaled by a
     * percentage (some value in the range [0, 1]).
     *
     * @param {Number} perc Value in the range [0, 1].
     * @param {Object} minRGB Has r, g, and b attributes in the range [0, 255].
     * @param {Object} maxRGB Has r, g, and b attributes in the range [0, 255].
     *
     * @returns {String} Hex color string of the format #RRGGBB.
     */
    function getNodeColorization(perc, minRGB, maxRGB) {
        // Linearly scale each RGB value between the extreme colors'
        // corresponding RGB values
        var red_i = perc * (mgsc.MAX_RGB.r - mgsc.MIN_RGB.r) + mgsc.MIN_RGB.r;
        var green_i = perc * (mgsc.MAX_RGB.g - mgsc.MIN_RGB.g) + mgsc.MIN_RGB.g;
        var blue_i = perc * (mgsc.MAX_RGB.b - mgsc.MIN_RGB.b) + mgsc.MIN_RGB.b;
        // Convert resulting RGB decimal values (should be in the range [0, 255])
        // to hexadecimal and use them to construct a color string
        var red = Math.round(red_i).toString(16);
        var green = Math.round(green_i).toString(16);
        var blue = Math.round(blue_i).toString(16);
        // Ensure that the color string is 6 characters long (for single-digit
        // channel values, we need to pad on the left with a zero)
        var channels = [red, green, blue];
        for (var ch = 0; ch < 3; ch++) {
            if (channels[ch].length === 1) {
                channels[ch] = "0" + channels[ch];
            }
        }
        return "#" + channels[0] + channels[1] + channels[2];
    }

    /* Given two points, each in the form [x, y], returns the distance between
     * the points obtained using d = sqrt((x2 - x1)^2 + (y2 - y1)^2).
     * e.g. distance([1, 2], [3, 4]) = sqrt((3 - 1)^2 + (4 - 2)^2) = sqrt(8)
     */
    function distance(point1, point2) {
        return Math.sqrt(
            Math.pow(point2[0] - point1[0], 2) +
                Math.pow(point2[1] - point1[1], 2)
        );
    }

    /* Given a line that passes through two points (linePoint1 and linePoint2),
     * this function returns the perpendicular distance from a point to the
     * line. This assumes all points are given as lists in the form [x, y].
     *
     * Note that, unlike most formulations of point-to-line-distance, the value
     * returned here isn't necessarily nonnegative. This is because Cytoscape.js
     * expects the control-point-distances used for unbundled-bezier edges to have
     * a sign based on which "side" of the line from source node to sink node
     * they're on:
     *
     *       negative
     * SOURCE ------> TARGET
     *       positive
     *
     * So here, if this edge has a bend "upwards," we'd give the corresponding
     * control point a negative distance from the line, and if the bend was
     * "downwards" it'd have a positive distance from the line. You can see this
     * for yourself here (http://js.cytoscape.org/demos/edge-types/) -- notice how
     * the control-point-distances for the unbundled-bezier (multiple) edge are
     * [40, -40] (a downward bend, then an upwards bend).
     *
     * What that means here is that we don't take the absolute value of the
     * numerator in this formula; instead, we negate it. This makes these distances
     * match up with what Cytoscape.js expects. (I'll be honest: I don't know why
     * this works. This is just what I found back in 2016. As a big heaping TODO,
     * I should really make this more consistent, or at least figure out *why* this
     * works -- it's worth noting that if you swap around linePoint1 and
     * linePoint2, this'll negate the distance you get, and I have no idea why this
     * is working right now.)
     *
     * Also note that, if distance(linePoint1, linePoint2) is equal to 0, this
     * will throw an Error (since this would make the point-to-line-distance
     * formula undefined, due to having 0 in the denominator). So don't define a
     * line by the same point twice!
     *
     * CODELINK: The formula used here is based on
     * https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line#Line_defined_by_two_points.
     */
    function pointToLineDistance(point, linePoint1, linePoint2) {
        var lineDistance = distance(linePoint1, linePoint2);
        if (lineDistance === 0) {
            throw new Error(
                "pointToLineDistance() given a line of the same point twice"
            );
        }
        var ydelta = linePoint2[1] - linePoint1[1];
        var xdelta = linePoint2[0] - linePoint1[0];
        var x2y1 = linePoint2[0] * linePoint1[1];
        var y2x1 = linePoint2[1] * linePoint1[0];
        var numerator = ydelta * point[0] - xdelta * point[1] + x2y1 - y2x1;
        return -numerator / lineDistance;
    }

    /**
     * Returns true if a number is a "valid integer," which to us just means
     * it's a string with just digits. Negative numbers are not allowed.
     *
     * This is an overly strict way of checking this, probably -- you could
     * imagine things like 1e2 being valid integers, in theory. But this hasn't
     * been a problem yet, so... I'm not going to bother changing this yet.
     * Plus I figure too strict is better than not strict enough.
     *
     * @param {String}
     * @returns {Boolean}
     */
    function isValidInteger(strVal) {
        return strVal.match(/^\d+$/) !== null;
    }

    function getHumanReadablePatternType(pattType) {
        var lctype = pattType.toLowerCase();
        if (lctype === "chain") {
            return "Chain";
        } else if (lctype === "cyclicchain") {
            return "Cyclic Chain";
        } else if (lctype === "bubble") {
            return "Bubble";
        } else if (lctype === "frayedrope") {
            return "Frayed Rope";
        } else {
            return pattType;
        }
    }

    /**
     * Converts user-input search text to an array of node names.
     *
     * Splits at commas, trims leading/trailing whitespace around each name,
     * and filters to unique names.
     *
     * @param {String} nameText
     *
     * @returns {Array} uniqueTrimmedNames
     *
     * @throws {Error} If nameText is empty, or if it only contains whitespace.
     *                 The error text returned here is designed to be human-
     *                 readable, so the caller can alert the user with it.
     */
    function searchNodeTextToArray(nameText) {
        // If only whitespace is given in the search input, alert the user.
        // I guess this assumes that node names do not just contain
        // whitespace. That should be a safe assumption...?
        if (nameText.trim() === "") {
            if (nameText.length > 0) {
                throw new Error(
                    "Only whitespace characters entered in the search text."
                );
            } else {
                throw new Error("Nothing entered in the search text.");
            }
        }
        var nodeNames = nameText.split(",");
        // Trim leading and trailing whitespace around node names
        var trimmedNodeNames = _.map(nodeNames, function (n) {
            return n.trim();
        });
        // Remove duplicate node names.
        // We *could* raise an error if there are duplicates (and alert the
        // user that "hey you entered 12 twice"), but I think just being
        // permissive is ok (the user should see "oh dang only 5 nodes are
        // selected but I entered 6 node names what gives oh wait nvm haha I
        // put 12 twice what a wacky and relatable user story").
        return _.uniq(trimmedNodeNames);
    }

    /**
     * Converts an Array to a human-readable String.
     *
     * The output String is surrounded by double quotation marks, and elements
     * are separated by a comma and space.
     *
     * e.g. arrToHumanReadableString(["abc", "def", "ghi"])
     * should produce '"abc, def, ghi"'.
     *
     * @param {Array} arr Non-empty Array of values.
     *
     * @returns {String} Human-readable string formatted as described above.
     *
     * @throws {Error} If arr is empty.
     */
    function arrToHumanReadableString(arr) {
        if (arr.length === 0) {
            throw new Error(
                "Passed an empty array to arrToHumanReadableString()."
            );
        }
        var s = '"';
        _.each(arr, function (val, i) {
            if (i > 0) {
                s += ", ";
            }
            s += val;
        });
        s += '"';
        return s;
    }

    /**
     * Given a number, converts to a String and makes it have two digits.
     *
     * e.g. leftPad(9) -> "09"
     *      leftPad(12) -> "12"
     *
     * @param {Number} x Must be an integer and in the range [0, 99], or this
     *                   will throw an error.
     *
     * @return {String} xPadded
     */
    function leftPad(x) {
        if (Number.isInteger(x)) {
            if (x >= 0 && x <= 99) {
                return String(x).padStart(2, 0);
            } else {
                throw new Error(
                    "Argument to leftPad() not in the range [0, 99]: " + x
                );
            }
        } else {
            throw new Error("Argument to leftPad() not an integer: " + x);
        }
    }

    /**
     * Returns a String timestamp of the format "YYYY-MM-DDThh:mm:ss".
     *
     * This should be https://xkcd.com/1179 compliant. And ISO-8601
     * compliant... uh, I think. Don't hold me to that :P
     *
     * Hours are in "military time" (American-speak for "5:00pm is 17:00")
     * because that's the default of Date.prototype.getHours().
     *
     * Intended to produce useful, non-overlapping filenames for screenshots.
     *
     * This should be decently robust, but if you're reading this because it
     * broke while you were in a plane across the date line on a leap year or
     * something then I am sorry, please go open an issue and yell at me.
     *
     * FYI -- If you want a timestamp from the current time, you can just call
     * getFancyTimestamp(new Date()).
     *
     * @param {Date} d Date object to convert to a timestamp.
     *
     * @returns {String} timestamp
     */
    function getFancyTimestamp(d) {
        var timestamp = "";
        timestamp += d.getFullYear() + "-";
        // Date.prototype.getMonth() is 0-indexed ._.
        timestamp += leftPad(d.getMonth() + 1) + "-";
        // ...but getDate() isn't. (I guess getHours(), getMinutes(), and
        // getSeconds() are, though? But those are already 0-indexed sooooo...)
        // Oh, also: the reason we use "T" to separate the date (YYYY-MM-DD)
        // and the time (hh:mm:ss) is because that's what ISO 8601 requires.
        timestamp += leftPad(d.getDate()) + "T";
        timestamp += leftPad(d.getHours()) + ":";
        timestamp += leftPad(d.getMinutes()) + ":";
        timestamp += leftPad(d.getSeconds());
        return timestamp;
    }

    return {
        getNodeColorization: getNodeColorization,
        distance: distance,
        pointToLineDistance: pointToLineDistance,
        isValidInteger: isValidInteger,
        getHumanReadablePatternType: getHumanReadablePatternType,
        searchNodeTextToArray: searchNodeTextToArray,
        arrToHumanReadableString: arrToHumanReadableString,
        getFancyTimestamp: getFancyTimestamp,
        leftPad: leftPad,
    };
});
