#! /usr/bin/fish
./graph_collator/collate.py -i testgraphs/ecoli/E_coli_LastGraph -o ecoli -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/sjackman/sample.gfa -o sample_gfa -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/sjackman/loop.gfa -o loop_gfa -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/sample_LastGraph -o sample_salmonella -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/longtest_LastGraph -o longtest -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/small_ecoli/oriented_lengthinfo.gml -o small_ecoli -d testdbs/ -w
./graph_collator/collate.py -i testgraphs/RF_oriented_lengthinfo.gml -o shakya -d testdbs/ -w
