"""
TODO we want to create a standardized IODevice for Vocabularies
"""

from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import DC, FOAF
from core.container.experiment import Vocabulary, VocabularyWord

from typing import List

class RDFVocabularyDevice():
    def import_(self):
        pass

    def export(self, vocabularies:List[Vocabulary]):
        pass


