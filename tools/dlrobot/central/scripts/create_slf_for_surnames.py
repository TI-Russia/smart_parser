from pylem import MorphanHolder, MorphLanguage, MorphSourceDictHolder
from common.logging_wrapper import setup_logging
from common.russian_fio import TRussianFioRecognizer
import json
from collections import defaultdict
import argparse

FEM_GENDER = "1"
MASC_GENDER = "2"

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", dest="input_json")
    parser.add_argument("--output-slf", dest="output_slf")
    parser.add_argument("--max-output-count", dest="max_output_count", type=int)
    parser.add_argument("--wikipedia-titles", dest="wikipedia_titles")
    parser.add_argument("--surname-prefix", dest="surname_prefix")
    args = parser.parse_args()
    return args


class TFio:
    def __init__(self, surname=None, name=None, patronymic=None, gender=None):
        self.surname = surname
        self.name = name
        self.patronymic = patronymic
        self.gender = gender

    def read_from_json(self, s):
        self.surname = s['s']
        self.name = s['n']
        self.patronymic = s['p']
        self.gender = s['g']
        return self


class TPredictor:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging("create_slf_for_surnames")
        mwz_path = 'C:/tmp/RML/Source/morph_dict/data/Russian/project.mwz'
        self.morph_wizard = MorphSourceDictHolder(mwz_path)
        self.morph = MorphanHolder(MorphLanguage.Russian)
        self.surnames = defaultdict(list)

    def read_wiki_titles(self):
        self.logger.info("read {}".format(self.args.wikipedia_titles))
        with open(self.args.wikipedia_titles) as inp:
            cnt = 0
            for l in inp:
                if l.count(',') != 1 and l.count('_') != 2:
                    continue
                words = l.strip().split('_')
                if len(words) != 3:
                    continue
                surname, name, patronymic = words
                if self.args.surname_prefix is not None and not surname.lower().startswith(self.args.surname_prefix):
                    continue
                surname = surname.strip(',')
                fem = TRussianFioRecognizer.is_feminine_patronymic(patronymic)
                masc = TRussianFioRecognizer.is_masculine_patronymic(patronymic)
                if not fem and not masc:
                    continue
                cnt += 1
                gender = FEM_GENDER if fem else MASC_GENDER
                self.surnames[surname.lower()].append(TFio(surname,name, patronymic, gender))
        self.logger.info("read {} fios from {}".format(cnt, self.args.wikipedia_titles))

    def read_fio_from_disclosures(self):
        self.logger.info("read {}".format(self.args.input_json))
        with open(self.args.input_json) as inp:
            for l in inp:
                fio = TFio().read_from_json(json.loads(l))
                if self.args.surname_prefix is not None and not fio.surname.lower().startswith(self.args.surname_prefix):
                    continue
                self.surnames[fio.surname.lower()].append(fio)

    def check_slf(self, slf):
        for l in slf.split("\n"):
            if l.startswith('$') or l.startswith('='):
                continue
            words = l.split()
            if len(words) > 0:
                if self.morph.is_in_dictionary(words[0]):
                    self.logger.debug("additional ambiguity, word form {}".format(words[0]))

    def predict_surnames(self, surname, outp):
        if surname.endswith('а') and surname[:-1] in self.surnames:
            self.logger.debug("ignore {} since masculine surname in in the list".format(surname))
            return

        if surname.endswith('ая') and (surname[:-2] + 'ий') in self.surnames:
            self.logger.debug("ignore {} since masculine surname in in the list".format(surname))
            return

        if surname.count('-') > 0:
            self.logger.debug("ignore {} since it contains a hyphen".format(surname))
            return

        genders = set (e.gender for e in self.surnames[surname])
        if len(genders) == 1 and FEM_GENDER in genders:
            if surname.endswith('ова')  or surname.endswith('ева') or surname.endswith('ина'):
                self.logger.debug("delete last char for popular fem surname {}".format(surname))
                surname = surname[:-1]
                genders = set([MASC_GENDER])
            else:
                self.logger.error("ignore {} since no masculine surname in in the example".format(surname))
                return

        predictions = self.morph_wizard.predict_lemm(surname, 3, 2)
        if len(predictions) == 0:
            self.logger.error("no predictions for {}".format(surname))
        else:
            surname_count = 0
            surname_index = -1
            for i in range(len(predictions)):
                if predictions[i].getCommonGrammems().find('surname') != -1:
                    surname_count += 1
                    surname_index = i
            if surname_count == 0:
                self.logger.error("no surname prediction for {}".format(surname))
            elif surname_count > 1:
                self.logger.error("more than one surname prediction for {}".format(surname))
            else:
                prd  = predictions[surname_index]
                wiki = prd.getWiktionaryTemplateRef()
                if wiki == "":
                    self.logger.error("weak (not wiktionary) surname paradigm for {}".format(surname))
                else:
                    self.logger.debug("predict {} flexia model={}, suffix freq={}".format(
                        surname, prd.getFlexiaModelNo(), prd.getFreq()
                    ))
                    slf = prd.getSlf(surname)
                    self.check_slf(slf)
                    outp.write(slf)

    def main(self):
        if self.args.wikipedia_titles is not None:
            self.read_wiki_titles()
        self.read_fio_from_disclosures()

        self.logger.info("process {} surname...".format(len(self.surnames.keys())))
        cnt = 0
        with open(self.args.output_slf, "w") as outp:
            for s in self.surnames.keys():
                if self.morph.is_in_dictionary(s):
                    self.logger.debug("{} is in dictionary".format(s))
                else:
                    self.predict_surnames(s, outp)
                cnt += 1
                if cnt % 1000 == 0:
                    print (".")
                if self.args.max_output_count is not None and cnt >= self.args.max_output_count:
                    break



if __name__ == "__main__":
    TPredictor().main()
