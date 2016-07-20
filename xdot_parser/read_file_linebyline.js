/* Enclosed is the code remaining from me trying to implement line-by-line
 * file reading for a few hours in the morning of June 21, 2016.
 * For .xdot files, reading the entire file at once might just make sense
 * (since the file format is relatively small?).
 * We can always change that up, too.
 */
if (!(window.File && window.FileReader && window.Blob)) {
	// TODO handle this better -- user should still be able to
	// play with sample assembly data
	// (or maybe support loading files some other non-HTML5 way?
	// something to look into)
	alert("Your browser does not support the HTML5 File APIs.");
}

//var cy = cytoscape({container: document.getElementById("cy")});

const FILEREADLEN = 64; // How many bytes to read at once

var currFilePos = 0; // will be updated as we read through the file
var currLineText = ""; // will be updated as we parse lines/parts-of-lines
var fr = new FileReader();

function loadxdot() {
	// Okay, so the ideal thing here would be to read this in line-by-line,
	// so we don't use an excessive amount of memory for large assembly
	// data files.
	// We can approximate this by using the "Blob" system.
	var xdotfile = document.getElementById('xdotselector').files[0];
	fr.onload = function(e) {
        // TODO account for EOF better
		if (e.target.readyState == FileReader.DONE) {
            currRead = e.target.result.split('\n');
            if (currRead.length == 1) {
                // There wasn't a newline in the read string
                currLineText += currRead[0];
                var endPos = currFilePos + FILEREADLEN;
                fragment = xdotfile.slice(currFilePos, endPos);
                currFilePos = endPos;
                fr.readAsText(fragment);
            } else {
                // We found a newline (potentially several)
                currLineText += currRead[0];
                document.getElementById("testspace").innerHTML += "<br />" + currLineText;
                // To be safe (but lazy), we only read one newline at a time
                var startPos = currFilePos + currRead[0].length;
                var endPos = startPos + FILEREADLEN;
                fragment = xdotfile.slice(startPos, endPos);
                currFilePos = endPos;
                currLineText = "";
                fr.readAsText(fragment);
            }
		}
	}
	var fragment = xdotfile.slice(currFilePos, currFilePos + FILEREADLEN);
	fr.readAsText(fragment);
    currFilePos = currFilePos + FILEREADLEN;
    // cy.add({ data: { id: 'node33' } });
    	
}

function itistimetostop() {
    fr.abort();
}
