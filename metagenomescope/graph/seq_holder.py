import os
import logging
import tempfile
import subprocess
import pyfastx as pf
from collections import defaultdict
from .. import name_utils, ui_utils
from ..errors import SeqParsingError, UIError


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
            logging.debug(f"  Writing out input FASTA to {tfp}...")
            with open(tfp, "w") as fh:
                fh.write(in_fasta)
            logging.debug("  ...Done. Indexing input FASTA...")

            try:
                subprocess.run(
                    ["bowtie2-build", "--quiet", tfp, tfp], check=True
                )
            except FileNotFoundError:
                raise UIError(
                    "Received a FileNotFoundError when using bowtie2-build. "
                    "Please make sure that bowtie2 is installed."
                )
            except subprocess.CalledProcessError:
                raise UIError(
                    "Creating an index using bowtie2-build failed. Please "
                    "make sure that you provided valid FASTA input above."
                )
            logging.debug("  ...Done. Running alignment...")

            # https://docs.python.org/3/library/subprocess.html#replacing-shell-pipeline
            afp = os.path.join(td, "aln.sam")
            # need -f because the "reads" (query sequences) are in FASTA
            # instead of FASTQ format
            try:
                subprocess.run(
                    [
                        "bowtie2",
                        "-x",
                        tfp,
                        "--quiet",
                        "--local",
                        "--no-unal",
                        "--no-head",
                        "-f",
                        self.fasta_fp,
                        "-S",
                        afp,
                    ],
                    check=True,
                )
            except FileNotFoundError:
                raise UIError(
                    "Received a FileNotFoundError when using bowtie2. "
                    "Please make sure that bowtie2 is installed."
                )
            except subprocess.CalledProcessError:
                raise UIError(
                    "Running bowtie2 failed. I'm not sure why this would "
                    "happen, since indexing the above FASTA apparently worked "
                    "out??? Please file an issue on MetagenomeScope's GitHub."
                )
            logging.debug("  ...Done. Parsing alignment...")

            # I am SURE there are faster ways to do this; see
            # https://github.com/samtools/samtools/issues/1672 for some
            # discussion
            inseq2graphseqs = defaultdict(set)
            num_alns = 0
            with open(afp, "r") as fh:
                for line in fh:
                    parts = line.split("\t")
                    inseq2graphseqs[parts[2]].add(parts[0])
                    num_alns += 1
            logging.debug(
                "  ...Done. "
                f"Found {ui_utils.pluralize(num_alns, 'alignment')}."
            )
        logging.debug("...Done.")
        return inseq2graphseqs
