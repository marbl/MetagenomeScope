import os
import logging
import tempfile
import subprocess
import pyfastx as pf
from collections import defaultdict
from .. import name_utils, ui_utils, aln_config
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

    def get_seq(self, seq_name):
        if seq_name in self.node_names_with_seqs:
            return self.f[seq_name]
        else:
            raise UIError(f'No sequence named "{seq_name}" in input FASTA.')

    def run_search(self, in_fasta, aligner=aln_config.MINIMAP2):
        if in_fasta is None:
            # can happen if the textarea is empty
            raise UIError("No sequence(s) given.")

        # Use a temporary directory instead of just a single temporary file,
        # since indexing will create a bunch of files that I don't want to
        # leave around (so that doing a bunch of searches won't clog up the
        # user's /tmp/ directory)
        with tempfile.TemporaryDirectory() as td:

            tfp = os.path.join(td, "in.fa")
            logging.debug(f"  Writing out input FASTA to {tfp}...")
            with open(tfp, "w") as fh:
                fh.write(in_fasta)
            logging.debug(f"  ...Done. Running {aligner}...")

            afp = os.path.join(td, "aln.paf")
            try:
                subprocess.run(
                    [
                        "minimap2",
                        "-x",
                        "sr",
                        tfp,
                        self.fasta_fp,
                        "-o",
                        afp,
                    ],
                    check=True,
                )
            except FileNotFoundError:
                raise UIError(
                    "Received a FileNotFoundError when trying to run "
                    "{aligner}. Please make sure that it is installed."
                )
            except subprocess.CalledProcessError as cpe:
                raise UIError(
                    f"Running {aligner} failed. Return code: {cpe.returncode}."
                )
            logging.debug("  ...Done. Parsing alignment...")

            # NOTE: since we haven't specified -a, -c, or --cs,
            # minimap2 will only output approximate mapping locations.
            # This should be okay if we are just checking for hits and don't
            # care abt exact locations within the sequences -- see
            # https://github.com/lh3/minimap2/blob/master/FAQ.md
            inseq2graphseqs = defaultdict(set)
            num_alns = 0
            with open(afp, "r") as fh:
                for line in fh:
                    parts = line.split("\t")
                    inseq2graphseqs[parts[5]].add(parts[0])
                    num_alns += 1
            logging.debug(
                "  ...Done. "
                f"Found {ui_utils.pluralize(num_alns, 'alignment')}."
            )
        return inseq2graphseqs
