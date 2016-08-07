# Features to add to the web application

* Display underlying DNA sequence of contig/selected group of contigs
    * e.g. for a frayed rope, [ATCG|TACG]CGAT[ATAC|ATTG]
    * ...for a bubble,      ATCG[CGAT|CGTT]TA
    * ...for a chain,       ATCG-CGTT-TTCG
    * ...for a cycle,       ...-ATCG-CGAT-...
    * Another cool feature to consider: for the current component, display
      its total number of contigs, their total length in bp, and (to make
      this really cool) the overall size of the entire graph, and the
      percentage of that that is taken up by the currently-being-viewed
      connected component.
    * Also, we should probably add in a mode to visualize all (or at least
      some user-specified permutation, like a comma list as used in the
      searching interface) of the connected components at once.
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
    * Just need to implement in renderEdgeObject().

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
    * Or use ANTLR or something for xdot parsing. Would take care of
      above point, and make modifying the xdot parser in the future (to add
      more features, etc.) a lot easier.

* Any other cool features.
