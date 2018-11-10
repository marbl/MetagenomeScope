#! /usr/bin/fish
# The testgraphs/ and testdbs/ directories are ignored in the git repository to
# save space. This is just a useful script I wanted to save that auto-updates a
# number of assembly graphs' corresponding .db files.
#
# Assumes the CWD is the root of the MetagenomeScope/ repository.
#
# TODO: remove a few things from here (unsimplified SRS049950?, 20170220, etc)
# that aren't needed any more.
# Also, either remove the P_ graphs from the demo or add them + the requisite
# input files to build them to this script.
./graph_collator/collate.py -i testgraphs/ecoli/E_coli_LastGraph -o ecoli -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/sjackman/sample.gfa -o sample_gfa -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/sjackman/loop.gfa -o loop_gfa -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/marygold_fig2a.gml -o marygoldtest -d testdbs/ -w -spqr
./graph_collator/collate.py -i testgraphs/sample_LastGraph -o sample_LastGraph -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/longtest_LastGraph -o longtest -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/small_ecoli/oriented_lengthinfo.gml -o small_ecoli -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/UpdatedBAMBUSfiles/shakya_oriented.gml -o shakya_new -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/august1.gml -o august1 -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/ship_hull_biofilm/oriented_judson.gml -o biofilm_judson -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/ship_hull_biofilm/oriented_judson_2.gml -o biofilm_judson2 -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/UpdatedBAMBUSfiles/oriented.gml -o 20170220 -d testdbs/ -w
echo "Creating the (unsimplified) Shakya graph. This might take a while."
./graph_collator/collate.py -i testgraphs/RF_oriented_lengthinfo.gml -o shakya -d testdbs/ -w
#echo "Creating the (unsimplified) SRS049950 graph. This might take a while."
#./graph_collator/collate.py -i testgraphs/august1_before_withlengthandfwdorients.gml -o august1_before -d testdbs/ -w
