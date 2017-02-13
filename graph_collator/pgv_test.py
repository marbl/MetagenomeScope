#!/usr/bin/env python
# exhibits the error described here --
# https://github.com/pygraphviz/pygraphviz/issues/113
# I'm running Debian 8.6 x86_64, using Python 2.7.9 and PyGraphViz 1.3.1.
# Component 108 of the Shakya scaffold graph
import pygraphviz
gv_input = """digraph asm {
	xdotversion=1.7;
	node [fixedsize=true];
	edge [headport=n,tailport=s];
	cluster_B12620_7813_9438_2566 [height=9.58333,width=5.80556,shape=rectangle];
	cluster_C5437_3721 [height=6.52778,width=3.05556,shape=rectangle];
	6203 [height=2.91275,width=2.91275,shape=invhouse];
	6859 [height=2.87448,width=2.87448,shape=invhouse];
	12207 [height=4.60568,width=4.60568,shape=invhouse];
	18519 [height=2.37107,width=2.37107,shape=invhouse];
	12613 [height=2.61384,width=2.61384,shape=invhouse];
	cluster_B12620_7813_9438_2566 -> 6203 [comment="2566,6203"]
	cluster_B12620_7813_9438_2566 -> 18519 [comment="2566,18519"]
	6203 -> 6859 [comment="6203,6859"]
	6203 -> 18519 [comment="6203,18519"]
	6859 -> cluster_C5437_3721 [comment="6859,5437"]
	12207 -> cluster_C5437_3721 [comment="12207,5437"]
	12613 -> cluster_B12620_7813_9438_2566 [comment="12613,12620"]
}"""
i = 1
while True:
    # Ideally, this would run forever (the same graph would be created and
    # then destroyed over and over again). However, that is not the case.
    h = pygraphviz.AGraph(gv_input)
    h.layout(prog='dot')
    print "hi"
    # This next step is what causes errors
    bb = h.graph_attr[u'bb']
    # Interestingly, adding a print statement after accessing bb seems to
    # prevent the segfault. Uncomment the below line to observe this.
    #print "bye"

    h.clear()
    h.close()
    i += 1
