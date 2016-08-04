# Features to add to the web application

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
    * It looks like neo4j needs a server to be running to interact with
      a database. Unfortunately, for the sort of use cases I was envisioning
      (users generate a database locally, and can host it on their server or
      load it directly into the AsmViz viewer), this isn't suitable, so it
      seems I might have to find another database type.
    * How does SQLite sound? It's lightweight, doesn't require a server,
      and very widely used (so lots of support exists for it -- both
      in pysqlite and somewhat less so in sql.js). --> Let's go with this
      for now.
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
            * Contig read depth (use to make nodes "wider"/thicker/thinner)
              From LastGraph, it looks like this can be calculated as
              O_COV_SHORT1 divided by COV_SHORT_1 (COV_SHORT_1 = contig
              length in bp).
            * Length (in base pairs) of contigs
            * etc.
    * Then we can load this database directly into the Javascript UI
    (we'd, uh, probably have to rename it from "xdot parser").
    This would also allow us to only render single connected components
    at a time, while allowing the user to switch between components
    within the interface (maybe by giving each node/edge a "component"
    attribute?). This could be pretty cool.
    * Another cool feature to consider: for the current component, display
      its total number of contigs, their total length in bp, and (to make
      this really cool) the overall size of the entire graph, and the
      percentage of that that is taken up by the currently-being-viewed
      connected component.
    * Also, we should probably add in a mode to visualize all (or at least
      some user-specified permutation) of the connected components at once.
      Although that could be pretty slow for large graphs, if the user
      wants to check multiple components at once for certain patterns/etc.
      then it could make sense.

* Think about how to linearly display the "longest path" through the graph,
or more specifically through an individual connected component. Will
definitely have to factor in node size here. THIS IS IMPORTANT!

* Hear back on how to interpret node size from GML files.

* Show multiple assembly files for the same data at once?
    * See [this Cytoscape.js demo](http://js.cytoscape.org/demos/310dca83ba6970812dd0/) for an example.

* Account for edge multiplicity in the graph (via altering edge with in
Cytoscape.js, and I think there's probably a way to do something similar in
GraphViz -- we'd want to do this in both environments, so the GraphViz
layout can support more separation for thicker edges) by displaying edges
with greater multiplicity values as thicker, as done in Figure 3 in the
Assembly Algorithms paper by Miller, Koren et al.
    * Just need to implement this on the Cytoscape.js side.

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

* Use ANTLR or something for xdot parsing. Would take care of above point.

* Any other cool features.
