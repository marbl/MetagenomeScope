import os
import logging
import tempfile
import subprocess
import pyfastx as pf
from .. import name_utils
from ..errors import SeqParsingError


class SeqHolder(object):
    """Holds sequence data.

    Currently this is super strict, for the sake of avoiding scope creep and
    getting this stuff done ASAP. Each sequence in the FASTA file must
    represent a forward node in the graph.

    Eventually we can do fancier stuff (supporting edge sequences for DOT
    graphs; indexing FASTG files directly rather than making the user specify
    a FASTA file for those; automatically extracting sequences from GFA /
    LastGraph files; ...) but for now this is enough. Maybe.
    """

    def __init__(self, fasta_fp, nodename2objs):
        self.f = pf.Fasta(fasta_fp)
        self.fasta_fp = fasta_fp
        self.node_names_with_seqs = set()
        self._record_seqs(nodename2objs)

    def _record_seqs(self, nodename2objs):
        """Populates self.node_names_with_seqs based on the FASTA file."""
        for seq_name in self.f.keys():
            if name_utils.is_rev(seq_name):
                raise SeqParsingError(f"FASTA contains - seq: {seq_name}")
            if name_utils.has_split_suffix(seq_name):
                raise SeqParsingError(f"FASTA contains split seq: {seq_name}")
            if seq_name not in nodename2objs:
                raise SeqParsingError(
                    f"Sequence {seq_name} is not a node in the graph"
                )
            if seq_name in self.node_names_with_seqs:
                raise SeqParsingError(
                    f"Sequence {seq_name} listed twice in the FASTA?"
                )
            self.node_names_with_seqs.add(seq_name)

    def __len__(self):
        """Returns the number of nodes with sequences given."""
        return len(self.node_names_with_seqs)

    def run_search(self, in_fasta):
        # TODO it would be good to do some sort of validation on this.
        # but in the meantime I guesssss we can leave that up to the aligner
        logging.debug("Running sequence search...")
        # Use a temporary directory instead of just a single temporary file,
        # since indexing will create a bunch of files that I don't want to
        # leave around (so that doing a bunch of searches won't clog up the
        # user's /tmp/ directory)
        with tempfile.TemporaryDirectory() as td:

            tfp = os.path.join(td, "in.fa")
            afp = os.path.join(td, "filtered-aln.sam")
            logging.debug(f"  Writing out input FASTA to {tfp}...")
            with open(tfp, "w") as fh:
                fh.write(in_fasta)
            logging.debug("  ...Done.")

            logging.debug("  Indexing input FASTA...")
            subprocess.run(["bowtie2-build", "--quiet", tfp, tfp])
            logging.debug("  ...Done.")

            # https://docs.python.org/3/library/subprocess.html#replacing-shell-pipeline
            logging.debug("  Running alignment and filtering to matches...")
            # need -f because the "reads" (query sequences) are in FASTA
            # instead of FASTQ format
            aln = subprocess.Popen(
                ["bowtie2", "-x", tfp, "--local", "-f", self.fasta_fp],
                stdout=subprocess.PIPE,
            )

            # use "samtools view -F 4" to get only the mapped query seqs
            # (i.e. the stuff in the FASTA file or whatever provided along
            # with the graph when starting up mgsc).
            samtools = subprocess.Popen(
                ["samtools", "view", "-F", "4", "-o", afp, "--no-header"],
                stdin=aln.stdout,
                stdout=subprocess.PIPE,
            )
            logging.debug("  ...Done.")

            aln.stdout.close()
            samtools.communicate()

            logging.debug("  Extracting match information...")
            # I am SURE there are faster ways to do this; see
            # https://github.com/samtools/samtools/issues/1672 for some
            # discussion
            names = set()
            with open(afp, "r") as fh:
                for line in fh:
                    names.add(line.split("\t")[0])
            logging.debug(f"  ...Done. Found {len(names):,} matches.")
        return names
