#! /usr/bin/env bash
# The testgraphs/ and testdbs/ directories are ignored in the git repository to
# save space. This is just a useful script I wanted to save that auto-updates a
# number of assembly graphs' corresponding .db files.
#
# Assumes the CWD is the root of the MetagenomeScope/ repository.

OUTPUT_DIR=testdbs/
mgsc -i testgraphs/ecoli/E_coli_LastGraph -o ecoli -d testdbs/ -w
mgsc -i testgraphs/sjackman/sample.gfa -o sample_gfa -d testdbs/ -w
mgsc -i testgraphs/sjackman/loop.gfa -o loop_gfa -d testdbs/ -w
mgsc -i testgraphs/marygold_fig2a.gml -o marygoldtest -d testdbs/ -w -spqr
mgsc -i testgraphs/sample_LastGraph -o sample_LastGraph -d testdbs/ -w
# NOTE longtest is currently not used on the demo but still nice to keep around
# for basic tests
mgsc -i testgraphs/longtest_LastGraph -o longtest -d testdbs/ -w
mgsc -i testgraphs/small_ecoli/oriented_lengthinfo.gml -o small_ecoli -d testdbs/ -w
mgsc -i testgraphs/UpdatedBAMBUSfiles/shakya_oriented.gml -o shakya_new -d testdbs/ -w
mgsc -i testgraphs/august1.gml -o august1 -d testdbs/ -w
mgsc -i testgraphs/ship_hull_biofilm/oriented_judson.gml -o biofilm_judson -d testdbs/ -w
mgsc -i testgraphs/ship_hull_biofilm/oriented_judson_2.gml -o biofilm_judson2 -d testdbs/ -w
echo "Creating the (unsimplified) Shakya graph. This might take a while."
mgsc -i testgraphs/RF_oriented_lengthinfo.gml -o shakya -d testdbs/ -w -maxe 10000
