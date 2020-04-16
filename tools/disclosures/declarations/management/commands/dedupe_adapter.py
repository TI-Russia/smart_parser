from .surname_freq import SurnameFreqDict
import declarations.models as models
from unidecode import unidecode
import django.core.exceptions
import json
import sys
import math
import logging
from deduplicate.config import resolve_fullname


class DedupeObjectJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if type(o) is frozenset:
            return list(o)
        else:
            return o


def dedupe_object_writer(s):
    return json.dumps(s, ensure_ascii=False, cls=DedupeObjectJsonEncoder)


def dedupe_object_reader(s):
    d = json.loads(s)
    converted_d = {}
    for k, v in d.items():
        if type(v) is list:
            converted_d[str(k)] = frozenset(v)
        else:
            converted_d[str(k)] = v
    return converted_d


def convert_vehicle(name):
    name = unidecode(name)
    name = name.replace(" ", "")
    name = name.replace("-", "")
    name = name.lower()
    return name


def prepareRussian(s):
    """ russian to english converter """
    if s is None:
        return ""
    return unidecode(s)



MAX_SURNAME_FREQ = max(SurnameFreqDict.values())


def get_surname_freq(surname):
    if surname == "":
        return 0
    freq = SurnameFreqDict.get(surname.lower(), 1)
    return round(math.log(MAX_SURNAME_FREQ / freq, 2), 4)


def try_to_float(float_str):
    try:
        if float_str is None:
            return 0
        return float(float_str)
    except:
        return 0


class TPersonNameInfo:
    def __init__(self, person_name):
        self.full_name = prepareRussian(person_name)
        self.family_name = ""
        self.patronymic = ""
        self.name = ""
        self.surname_freq = 0
        if person_name is not None and len(person_name) > 0:
            fio = resolve_fullname(person_name)
            if fio:
                self.surname_freq = get_surname_freq(fio['family_name'])
                self.family_name = prepareRussian(fio['family_name'])
                self.patronymic = prepareRussian(fio['patronymic'])
                self.name = prepareRussian(fio['name'])
                # this regularization deletes "." from full name "Sokirko V.V." ->  "Sokirko V V"
                self.full_name = " ".join((self.family_name, self.name, self.patronymic))
        if len(self.patronymic) == 0:
            self.patronymic = "_"   #dedupe failed  on empty lines
        if len(self.name) == 0:
            self.name = "_"   #dedupe failed  on empty lines
        self.patronymic_char = prepareRussian(self.patronymic[0]) if self.patronymic and len(self.patronymic) else ""
        self.name_char = prepareRussian(self.name[0]) if self.name and len(self.name) else ""

    def get_short_name(self):
        return " ".join((self.family_name, self.name_char, self.patronymic_char))

    def get_fio_trigram(self):
        return " ".join((self.family_name[0], self.name_char, self.patronymic_char))


class TSectionFields:
    """ Prepares Section object for dedupe routines """

    def __init__(self, s):
        self.id = s.id
        self.person_income = next((i.size for i in s.income_set.all() if i.relative == models.Relative.main_declarant_code), None)
        self.spouse_income = next((i.size for i in s.income_set.all() if i.relative == models.Relative.spouse_code), None)
        self.year = s.income_year
        self.office = unidecode(s.spjsonfile.office.name)
        self.position = unidecode("" if s.position is None else s.position)
        self.realestates = [try_to_float(i.square) for i in s.realestate_set.all()]
        self.children_number = len([i for i in s.realestate_set.all() if (i.relative == models.Relative.child_code)])
        self.children_real_estate = sum(
            [try_to_float(i.square) for i in s.realestate_set.all() if (i.relative == models.Relative.child_code)])
        self.vehicles = [convert_vehicle(i.name) for i in s.vehicle_set.all() if i.name]
        self.person_name_info = TPersonNameInfo (s.person_name)


def avg(values):
    n = 0
    summ = 0.0
    for v in values:
        if v is not None:
            summ += v
            n += 1
    if n == 0:
        return 0
    return summ / n


class TPersonFields:
    """ Prepares Person object for dedupe routines """

    def __init__(self, person=None, section=None):
        if person is not None:
            assert (section is None)
            self.id = "person-" + str(person.id)
            section_set = list(person.section_set.all())
            max_person_name = ""
            for s in section_set:
                if len(s.person_name) > len(max_person_name):
                    max_person_name = s.person_name
            self.person_name_info = TPersonNameInfo(max_person_name)
            self.sections = [TSectionFields(s) for s in section_set]
        else:
            assert (section is not None)
            self.id = "section-" + str(section.id)
            self.sections = [TSectionFields(section)]
            self.person_name_info = self.sections[0].person_name_info

    def get_short_name(self):
        return self.person_name_info.get_short_name()

    def get_fio_trigram(self):
        return self.person_name_info.get_fio_trigram()

    def get_offices(self):
        return " ".join(set(s.office for s in self.sections))

    def get_income(self):
        return avg(s.person_income for s in self.sections)

    def get_years_str(self):
        return " ".join(str(s.year) for s in self.sections)

    def get_dedupe_id_and_object(self, filter_function=None):
        sections = [s for s in self.sections if (filter_function is None or filter_function(s))]
        if len(sections) == 0:
            return None, None

        if filter_function is None:
            id = self.id
        else:
            id = " ".join(str(s.id) for s in sections)

        full_name = self.person_name_info.full_name

        return id, {
            'full_name': full_name.lower(),
            'family_name': self.person_name_info.family_name.lower(),
            'patronymic_char': self.person_name_info.patronymic_char.lower(),
            'name_char': self.person_name_info.name_char.lower(),
            'person_income': avg(s.person_income for s in sections),
            'spource_income': avg(s.spouse_income for s in sections),
            'min_year': min(s.year for s in sections),
            'realestates': frozenset(r for s in sections for r in s.realestates),
            'realestates_shared_size': frozenset(r for s in sections for r in s.realestates),
            'children_number': avg(s.children_number for s in sections),
            'children_real_estate': avg(s.children_real_estate for s in sections),
            'surname_freq': self.person_name_info.surname_freq,
            'vehicles': frozenset(r for s in sections for r in s.vehicles),
            'offices': frozenset(s.office for s in sections),
            'roles': frozenset(s.position for s in sections)
        }


def describe_dedupe(stdout, dedupe):
    stdout.write("Dedupe blocking predicates:")
    for p in dedupe.predicates:
        stdout.write("\t" + repr(p))
    stdout.write("ML type: {}\n".format(type(dedupe.classifier)))
    stdout.write("ML weights:" + "\n")
    if hasattr(dedupe.classifier, "weights"):
        weights = dedupe.classifier.weights
    else:
        weights = dedupe.classifier.feature_importances_
    weights_str = "\n".join(map(repr, zip(dedupe.data_model.primary_fields, weights)))
    stdout.write(weights_str + "\n")


def get_pairs_from_clusters(clustered_dupes, threshold=0):
    for (cluster_id, cluster) in enumerate(clustered_dupes):
        id_set, scores = cluster
        for id1, score1 in zip(id_set, scores):
            for id2, score2 in zip(id_set, scores):
                if id1 == id2:
                    continue
                if score1 > threshold and score2 > threshold:
                    if id1 < id2:
                        yield id1, id2, str(score1), str(score2)
                    else:
                        yield id2, id1, str(score2), str(score1)


def convert_to_dedupe(id):
    if id.startswith("section-"):
        section_id = int(id[len("section-"):])
        try:
            s = models.Section.objects.get(id=section_id)
        except models.Section.DoesNotExist:
            return None, None
        return TPersonFields(None, s).get_dedupe_id_and_object()
    elif id.startswith("person-"):
        person_id = int(id[len("person-"):])
        try:
            p = models.Person.objects.get(id=person_id)
        except models.Person.DoesNotExist:
            return None, None
        return TPersonFields(p).get_dedupe_id_and_object()
    else:
        assert False


def pool_to_dedupe(pairs, single_objects, match, distinct, ignore_empty=True):
    """ Converts pairs to Dedupe dicts, sets missing objects of the input pairs to UNK
    """
    logger = logging.getLogger('dedupe_declarator_logger')

    sys.stdout.flush()
    missing_cnt = 0
    processed_cnt = 0
    for (id1, id2), mark in pairs.items():
        try:
            processed_cnt += 1
            if processed_cnt % 100 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
            k1, v1 = convert_to_dedupe(id1)
            if k1 is None:
                raise django.core.exceptions.ObjectDoesNotExist()
            single_objects[k1] = v1
            k2, v2 = convert_to_dedupe(id2)
            if k2 is None:
                raise django.core.exceptions.ObjectDoesNotExist()
            single_objects[k2] = v2
            if mark == "YES":
                match.append((v1, v2))
            elif mark == "NO":
                distinct.append((v1, v2))
        except django.core.exceptions.ObjectDoesNotExist as e:
            missing_cnt += 1
            assert ignore_empty
            logger.debug("set pair {0} {1} to UNK, since one them is not found in DB".format(id1, id2))
            pairs[(id1, id2)] = 'UNK'

    logger.info("\nconvert pool to dedupe: pool size = {0}, missing_count={1}\n".format(
        processed_cnt, missing_cnt
    ))
