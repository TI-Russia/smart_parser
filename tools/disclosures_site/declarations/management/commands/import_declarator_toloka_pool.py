import csv
import json
import os
import logging
from django.core.management import BaseCommand
from declarations.common import resolve_fullname
import declarations.models as models
from declarations.serializers import TSmartParserJsonReader, TSectionPassportFactory
import pickle


class ConvertException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return (repr(self.value))


def check_family_name(n1, n2):
    fio1 = resolve_fullname(n1)
    fio2 = resolve_fullname(n2)
    if fio1 is None or fio2 is None:
        return n1[0:3].lower() == n2[0:3].lower()
    return fio1['family_name'].lower() == fio2['family_name'].lower()


def setup_logging(logfilename="convert_pool.log"):
    logger = logging.getLogger("convert_pool")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    return logger


class TDbSqueeze:
    def __init__(self):
        self.office_hierarchy = None
        self.stable_key_to_sections = None
        self.declarator_person_id_to_person_id = None

    def build_squeeze(self, logger):
        logger.info("build office hierarchy")
        self.office_hierarchy = models.TOfficeTableInMemory()

        logger.info("build all passports")
        factories = TSectionPassportFactory.get_all_passport_factories(self.office_hierarchy)
        self.stable_key_to_sections = TSectionPassportFactory.get_all_passports_dict(factories)

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
            json_file = models.Source_Document(office_id=sections[0].get('office_id', -1))
            passport_factory = TSmartParserJsonReader(year, json_file, sections[0]).get_passport_factory(
                self.squeeze.office_hierarchy)
            section_id, search_results = passport_factory.search_by_passports(self.squeeze.stable_key_to_sections)
            if section_id is not None:
                row[id_index] = str("section-") + str(section_id)
            else:
                raise ConvertException("cannot find in disclosures declarator section_id={}, passport={}, "
                                       "search_results={} ".format(
                    section_or_person_id,
                    passport_factory.get_passport_collection()[0],
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
        self.logger = setup_logging()
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



