# Features to add to the web application

* Add dynamic rotation status message? Should be simple to do, and would
  be useful when rotating large graphs (e.g. RF\_oriented\_1.xdot)
* Display underlying DNA sequence of contig/selected group of contigs
    * e.g. for a frayed rope, [ATCG|TACG]CGAT[ATAC|ATTG]
    * ...for a bubble,      ATCG[CGAT|CGTT]TA
    * ...for a chain,       ATCG-CGTT-TTCG
    * ...for a cycle,       ...-ATCG-CGAT-...
	* To get this working, I'll need to extract more information in the
	python script. Or I can just get the web tool to look at the
	assembly data file. But either way, I need to maintain a mapping of
	contig IDs to DNA sequences, and ideally I wouldn't create a new
	file to do this in: that would be silly for huge assembly files.
    * Use a neo4j graph database to store both biological data/metadata
      (e.g. DNA sequences of contigs, edge multiplicity, contig length in
      bp) and xdot layout data (parsing the xdot file from within
      collate\_clusters.py?), enabling us to just pass the database file to
      the parser interface.
        * So would we create multiple databases (one per component), or just
        one for the entire graph (and then split by components in the JS
        UI?) I guess the second option would support better switching
        between components, particularly depending on the sort of searches
        neo4j supports.
    * Alright, it looks like [py2neo](http://py2neo.org/v3/) is what
    we're looking for -- we can use it to generate, say, a file
    containing nodes, edges, node groups, and the relationships between
    them, along with:
        * layout/control point/etc. data
        (taken from the xdot file -- either
        pipe it directly from GraphViz to the Python script or read it
        from the finished .xdot file and delete that afterward) for each
        node and edge
        * biological data/metadata for each node (contig)/edge:
            * Underlying DNA sequence, if available (GML doesn't
            contain this, but LastGraph does)
            * Edge multiplicity (use to make edges thicker/thinner)
            * Contig read depth (use to make nodes thicker/thinner)
            * Length (in base pairs) of contigs
            * etc.
    * Then we can load this database directly into the Javascript UI
    (we'd, uh, probably have to rename it from "xdot parser").
    This would also allow us to only render single connected components
    at a time, while allowing the user to switch between components
    within the interface (maybe by giving each node/edge a "component"
    attribute?). This could be pretty cool.
	
	* OKAY, here's an idea:
	we modify GraphViz to somehow take a bogus
	entry in a .gv (DOT) file and copy it, verbatim, to XDOT. So, we'd
	give each node (contig) a dna_length, dna_fwdseq, and dna_revseq
	input (self-explanatory; note that some file formats, e.g. GML,
	might not contain all this info (we'll have to adjust the JS user
	interface according to the assembly graph input file format; maybe
	send that along as a bogus graph property, in a similar method?)),
	and we'd give each edge (arc) a multiplicity input. We can thus
	read these things in xdot2cy.js, store them in the internal backing
	classes for nodes and edges, and access them easily in the user
	interface.

* Open parser interface when we've finished laying out the first connected
component? We'd have to access the system's default internet browser and
then open the parser interface thing with the xdot file in question,
presumably (just spitballing here) by encoding a GET request in the URL
for that xdot file name. (This is a lot of work for a small payoff, so IDK.)
We might also want to show progress of connected components (e.g. 20/123
laid out) to user in the JS UI.

* In collate\_clusters.py:
  Provide user with time estimate, instead of using dot -v? We can base this
  off number of nodes/edges, etc.

* Modify xdot2cy.js to take a folder of xdot files as argument, and
facilitate the user cycling through the xdot files by size (provide a
"left/right" button? can refine UI with Dr. Pop and Todd next week.)
	* Doesn't look like HTML5 supports this, at least any more.

* Lay out the graph horizontally/at arbitrary angles. DONE.
	* TODO: Have this configurable by the user (text entry or selection
	 drop-down box for limited number of angles, with default of
	 90 degrees CCW or 270 degrees CW)
    * TODO: To make further use of this, add a (functional) horizontal
     scrollbar to traverse the graph in addition to dragging. We could even
     get keyboard support for this, maybe?

* Look into how GraphViz converts inches to pixels. See if we can manage to
factor INCHES\_TO\_PIXELS into the position layout of the graph (=50 works
fine, but we should support scaling the entire graph -- not just nodes --
with larger or smaller factors).

* Improve efficiency of reading+parsing the xdot file. Really, the file
should only be read through once, using blobs; don't do the thing of getting
the entire thing at once, reading it into memory, and then iterating through
it line by line. That's hugely inefficient for large files, and while it's
alright for a demo like this we'll want it to be more efficient for actual
use.

* Think about how to linearly display the "longest path" through the graph,
or more specifically through an individual connected component. Will
definitely have to factor in node size here. THIS IS IMPORTANT!

* Hear back on how to interpret node size from GML files.

* Show multiple assembly files for the same data at once?
    * See [this Cytoscape.js demo](http://js.cytoscape.org/demos/310dca83ba6970812dd0/) for an example.

* File more issue reports with Cytoscape.js. Remaining errors:
    * unbundled-bezier causing the need for control-point-distances attributes for every element in the graph
        * I need to actually work on getting this in a Minimal Working Example; for all I know this could just be some elaborate bug I accidentally introduced with data(cpd).
    * Documentation might be wrong re: the edge weights supported by
      Floyd-Warshall and Bellman-Ford algorithms (it should say "numeric,"
      instead of "positive numeric" -- would need to verify this and then
      submit a small pull request, I guess).

* Account for edge multiplicity in the graph (via altering edge with in
Cytoscape.js, and I think there's probably a way to do something similar in
GraphViz -- we'd want to do this in both environments, so the GraphViz
layout can support more separation for thicker edges) by displaying edges
with greater multiplicity values as thicker, as done in Figure 3 in the
Assembly Algorithms paper by Miller, Koren et al.
	* This can probably be worked in after developing a way to associate
	 arbitrary information (e.g. DNA sequences) with nodes/edges in the
	 graph and sending that information to the xdot parser/renderer.
	 From there it should be trivial to pass multiplicity information
	 and scale edge widths accordingly.

* Write parsers for the other 2 types of assembly files Todd wanted me to
support (GFA and FASTG), and also maybe for the Trinity FASTA file
(but honestly I have no idea how to read those).

* Look into "efficient bubble detection" (Fasulo et al. 2002). To be fair,
this might be for assemblers -- I'd guess that for assembly graphs already
prepared, finding bubbles isn't that difficult. (Although longer bubbles
may be a more difficult case.)
	* Pattern detection in the python script is already pretty
	 efficient, even for large graphs (for RF_oriented.gml, which has
	 ~21k nodes and ~21k edges, the entire python thing takes maybe
	 around 0.5 seconds to complete. The bottleneck here is by far
	 GraphViz laying out the graph.

* Tighten up xdot regexes to reject invalid numbers and alert the user to
their existence.

* Write an actual tokenizer for the xdot file format, so we can parse it
agnostic to spaces/formatting. Note that, as I lack a formal specification
of the xdot grammar, I'll probably have to come up with something myself.

* Any other cool features.
