#obsolete script, it is cheapier and better to create a new toloka pool than to import old pools
import office_db.offices_in_memory
from common.russian_fio import TRussianFio
import declarations.models as models
from declarations.serializers import TSmartParserSectionJson
from declarations.section_passport import TSectionPassportItems1
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
import csv
import json
import os
import pickle


class ConvertException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return (repr(self.value))


def check_family_name(n1, n2):
    fio1 = TRussianFio(n1)
    fio2 = TRussianFio(n2)
    if not fio1.is_resolved or not fio2.is_resolved:
        return n1[0:3].lower() == n2[0:3].lower()
    return fio1.family_name == fio2.family_name




class TDbSqueeze:
    AMBIGUOUS_KEY = "AMBIGUOUS_KEY"

    def __init__(self):
        self.office_hierarchy = None
        self.stable_key_to_sections = None
        self.declarator_person_id_to_person_id = None

    #was not tested!
    def get_all_passports_dict(self):
        passport_to_id = dict()
        section_passport_items = TSectionPassportItems1.get_section_passport_components()

        for (id, passport_items) in section_passport_items:
            for passport in passport_items.get_all_passport_variants_for_toloka_pool(self.office_hierarchy):
                search_result = passport_to_id.get(passport)
                if search_result is None:
                    passport_to_id[passport] = id
                elif search_result != id:  # ignore the same passport
                    passport_to_id[passport] = TDbSqueeze.AMBIGUOUS_KEY
        return passport_to_id

    def build_squeeze(self, logger):
        logger.info("build office hierarchy")
        self.office_hierarchy = office_db.offices_in_memory.TOfficeTableInMemory()
        self.office_hierarchy.read_from_table(models.Office.objects.all())

        logger.info("build all passports")
        self.stable_key_to_sections = self.get_all_passports_dict()

        logger.info("build declarator person id to person id")
        self.declarator_person_id_to_person_id = dict()
        for p in models.Person.objects.filter(declarator_person_id__isnull=False):
               self.declarator_person_id_to_person_id[p.declarator_person_id] = (p.id, p.person_name)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            dest='action',
            default="import",
            required=False,
            help="can be prepare or import",
        )
        parser.add_argument(
            '--input-pools',
            dest='input_pools',
            nargs="+",
            required=False,
        )
        parser.add_argument(
            '--output-folder',
            dest='output_folder',
            required=False,
        )

    def __init__(self,   *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = None
        self.squeeze = TDbSqueeze()
        self.squeeze_pickled_file_path = "squeeze.pickle"

    def search_by_passports(self, passport_items):
        # used only in toloka pool import
        search_results = list()
        res = None
        passport_variants = passport_items.get_all_passport_variants_for_toloka_pool(self.squeeze.office_hierarchy)
        for passport in passport_variants:
            res = self.squeeze.stable_key_to_sections.get(passport)
            if res is not None and res != TDbSqueeze.AMBIGUOUS_KEY:
                return res, search_results
            search_results.append(res)

        if res == TDbSqueeze.AMBIGUOUS_KEY:
            res = None
        return res, search_results

    def convert_one_id(self, header, section_or_person_id_key, json_key, row):
        id_index = header.index(section_or_person_id_key)
        assert id_index != -1
        section_or_person_id = row[id_index]
        json_index = header.index(json_key)
        assert json_index != -1
        person_json = json.loads(row[json_index])
        sections = person_json.get('sections', [])
        if len(sections) == 0:
            raise ConvertException("cannot find sections or bad format for id: {}".format(section_or_person_id))
        if 'person' in  sections[0]:
            input_person_name = sections[0]['person']['name_raw']
        else:
            input_person_name = person_json['fio']

        if section_or_person_id.startswith('person-'):
            declarator_person_id = int(section_or_person_id[len('person-'):])
            if declarator_person_id not in self.squeeze.declarator_person_id_to_person_id:
                raise ConvertException(
                    "declarator_person_id {} cannot be found in disclosures, skip this record".format(
                        declarator_person_id))
            person_id, person_name =  self.squeeze.declarator_person_id_to_person_id.get(declarator_person_id)
            if not check_family_name(person_name, input_person_name):
                raise ConvertException("person id: {} has a different family name, skip this record".format(person_id))
            row[id_index] = str("person-") + str(person_id)
        else:
            assert section_or_person_id.startswith('section-')
            year = sections[0].get('year', 0)
            office_id = office_id=sections[0].get('office_id', -1)
            json_file = models.Source_Document()
            passport_items = TSmartParserSectionJson(year, office_id, json_file).read_raw_json(sections[0]).get_passport_components1()
            section_id, search_results = self.search_by_passports(passport_items)
            if section_id is not None:
                row[id_index] = str("section-") + str(section_id)
            else:
                raise ConvertException("cannot find in disclosures declarator section_id={}, passport={}, "
                                       "search_results={} ".format(
                    section_or_person_id,
                    passport_items.get_main_section_passport(),
                    search_results))

    def convert_pool(self, input_file_name, output_folder):
        output_lines = list()
        header = list()
        self.logger.info("read file {}".format(input_file_name))
        with open(input_file_name, "r") as tsv:
            csv_reader = csv.reader(tsv, delimiter="\t")
            for task in csv_reader:
                header = task
                break
            if 'INPUT:id_left' not in header:
                raise Exception("unknown pool format")
            row_index = 0
            good_lines = 0
            for task_row in csv_reader:
                row_index += 1
                try:
                    if ''.join(task_row).strip() != '':
                        self.convert_one_id(header, 'INPUT:id_left', 'INPUT:json_left', task_row)
                        self.convert_one_id(header, 'INPUT:id_right', 'INPUT:json_right', task_row)
                    output_lines.append(task_row)
                    good_lines += 1
                except (ConvertException, models.Person.DoesNotExist) as exp:
                    self.logger.error("Line: {}, Exception: {}, continue\n".format(row_index, exp))
            self.logger.info("converted {} {} lines out of {} lines".format(input_file_name, good_lines, row_index))

        if len(output_lines) == 0:
            raise Exception("cannot convert file {}, no converted lines".format(input_file_name))

        output_path = os.path.join(output_folder, os.path.basename(input_file_name))
        self.logger.info("write to file {}".format(output_path))
        with open(output_path, 'w') as out_file:
            tsv_writer = csv.writer(out_file, delimiter="\t")
            tsv_writer.writerow(header)
            for row in output_lines:
                tsv_writer.writerow(row)

    def handle(self, *args, **options):
        self.logger = setup_logging(log_file_name="convert_pool.log")
        action = options['action']
        if action == "prepare":
            self.squeeze.build_squeeze(self.logger)
            self.logger.info("write to {}".format(self.squeeze_pickled_file_path))
            with open(self.squeeze_pickled_file_path, 'wb') as f:
                pickle.dump(self.squeeze, f)
        elif action == "import":
            if not os.path.exists(self.squeeze_pickled_file_path):
                raise Exception("please create file {} with python3 manage.py import_declarator_toloka_pool --action prepare --settings disclosures.settings.prod".format(self.squeeze_pickled_file_path))
            self.logger.info("read {}".format(self.squeeze_pickled_file_path))
            with open(self.squeeze_pickled_file_path, 'rb') as f:
                self.squeeze = pickle.load(f)
            self.logger.info("start conversion ...")
            for f in options['input_pools']:
                self.convert_pool(f, options['output_folder'])
        else:
            self.logger.error("unknown action {}".format(action))



