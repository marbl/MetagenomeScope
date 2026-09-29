from .. import name_utils
from ..errors import SeqParsingError
import pyfastx as pf

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
        self.f = pyfastx.Fasta(self.fasta_filename)
        self.nodes_with_seqs = set()
        self._record_seqs(self.f)

    def _record_seqs():
        """Populates self.nodes_with_seqs based on the FASTA file."""
        for seq_name in self.f:
            if name_utils.is_rev(seq_name):
                raise SeqParsingError(f"FASTA contains - seq: {seq_name}")
            if name_utils.has_split_suffix(seq_name):
                raise SeqParsingError(f"FASTA contains split seq: {seq_name}")
            if seq_name not in nodename2objs:
                raise SeqParsingError(
                    f"Sequence {seq_name} is not a node in the graph"
                )
            if seq_name in self.nodes_with_seqs:
                raise SeqParsingError(
                    f"Sequence {seq_name} listed twice in the FASTA?"
                )
            self.nodes_with_seqs.add(seq_name)

    def __len__(self):
        """Returns the number of nodes with sequences given."""
        return len(self.nodes_with_seqs)
