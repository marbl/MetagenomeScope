# Features to add to the web application

* Display underlying DNA sequence of contig/selected group of contigs
	* To get this working, I'll need to extract more information in the
	python script. Or I can just get the web tool to look at the
	assembly data file. But either way, I need to maintain a mapping of
	contig IDs to DNA sequences, and ideally I wouldn't create a new
	file to do this in: that would be silly for huge assembly files.
	
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

* Provide user with time estimate, instead of using dot -v? We can base this
off number of nodes/edges, etc.

* Highlight *all* bubbles/ropes/chains/cycles, etc., and then highlight
everything at once? Pro is more info displayed, con is it'll look really
confusing and will be super difficult to collapse.
	* We could also do something like "Make chains as long as possible
	at the detriment of detecting bubbles/ropes" for each node group
	type, I suppose, but that might be sort of silly.

* Modify xdot2cy.js to take a folder of xdot files as argument, and
facilitate the user cycling through the xdot files by size (provide a
"left/right" button? can refine UI with Dr. Pop and Todd next week.)
	* Doesn't look like HTML5 supports this, at least any more.

* Lay out the graph horizontally/at arbitrary angles. DONE.
	* TODO: Have this configurable by the user (text entry or selection
	 drop-down box for limited number of angles, with default of
	 90 degrees CCW or 270 degrees CW)

* Look into how GraphViz converts inches to pixels. See if we can manage to
factor INCHES_TO_PIXELS into the position layout of the graph (=50 works
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

* Make finding bubbles/ropes an inherently symmetric process -- for LastGraph
files, where we have the reverse complement of each node given, whenever we
discover a bubble or rope we also tag the RC of that bubble or rope (i.e.
the same nodes, but flipped in the opposite direction) as a bubble/rope.
This ensures things are symmetric and everything, and might actually make
the process of finding a bubble/rope go faster. (Of course, this isn't
achievable with, say, GML files where we don't know the RC of a given node)
	* NOTE that we don't need to worry about this with chains or cycles,
	 since those are guaranteed to always find every chain/cycle in the
	 graph (except for interfering nodes that are parts of other node
      	 groups, but it should be alright)

* Hear back on how to interpret node size from GML files.

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

* Highlight longer bubbles (as seen in the Miller et al. paper)/frayed ropes.
	* This should be achievable by detecting chains first, and then (for
	 frayed ropes) checking if using the entire chain as a "middle node"
	 would work or (for bubbles) checking if a node diverges to multiple
	 chains/single nodes and then converges to a single node from those
	 chains.
	 From there, we can remove the chains in question from the graph
	 and add their elements as "LongRopes" or "LongBubbles"
	 (or, uh, just normal ropes/bubbles) to the graph.

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
