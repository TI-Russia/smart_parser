import json
from declarations.models import SynonymClass
import sys
import os
sys.path.append (os.path.join(os.environ.get('RML'), "build/Source/lemmatizer_python"))
import aot

aot.load_morphology(1, False)


def get_word_forms(lemma, grammems):
    resp = aot.synthesize(lemma, grammems)
    for f in json.loads(resp)['forms']:
        yield f.lower()


def set_colloc_to_genitive_case(logger, colloc, syn_class):
    tokens = list(colloc.split(" "))
    genitive_forms = set()
    if len(tokens) == 1:
        for f in get_word_forms(tokens[0], "N gen,sg"):
            if f not in v['synonyms']:
                logger.debug("genitive {} -> {}".format(tokens[0], f))
                genitive_forms.add(f)
    elif len(tokens) == 2:
        if syn_class == SynonymClass.RussianWithTypeBefore:
            for f in get_word_forms(tokens[0], "N gen,sg"):

    return genitive_forms
