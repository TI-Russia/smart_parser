import csv
import json
from django.core.management import BaseCommand
from .common import resolve_fullname
import declarations.models as models
from datetime import datetime
from declarations.serializers import TSmartParserJsonReader, TSectionPassportFactory


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


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--input-pool',
            dest='input_pool'
        )
        parser.add_argument(
            '--output-pool',
            dest='output_pool',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.office_hierarchy = models.TOfficeHierarchy()
        factories = TSectionPassportFactory.get_all_passport_factories(self.office_hierarchy)
        #factories = TSectionPassportFactory.get_all_passport_factories()
        self.stable_key_to_sections = TSectionPassportFactory.get_all_passports_dict(factories)

    def log(self, msg):
        self.stdout.write('{}'.format(datetime.now()) + (' - ' + msg) if msg else '')

    def convert_line(self, header, section_or_person_id_key, json_key, row):
        id_index = header.index(section_or_person_id_key)
        assert id_index != -1
        section_or_person_id = row[id_index]
        json_index = header.index(json_key)
        assert json_index != -1
        person_json = json.loads(row[json_index])
        sections = person_json.get('sections', [])
        if len(sections) == 0:
            raise ConvertException("cannot find sections or bad format for id: {}".format(section_or_person_id))
        input_person_name = sections[0]['person']['name_raw']
        assert sections[0]['source'] == "declarator"
        if section_or_person_id.startswith('person-'):
            person_id = int(section_or_person_id[len('person-'):])
            person = models.Person.objects.get(id=person_id)
            person_sections = list(person.section_set.all())
            if not check_family_name(person_sections[0].person_name, input_person_name):
                raise ConvertException("person id: {} has a different family name, skip this record".format(person_id))
            return # nothing to set just check that it is the right person
        else:
            assert section_or_person_id.startswith('section-')
            year = sections[0].get('year', 0)
            json_file = models.SPJsonFile(office_id=sections[0].get('office_id', -1))
            passport_factory = TSmartParserJsonReader(year, json_file, sections[0]).get_passport_factory(self.office_hierarchy)
            section_id, search_results = passport_factory.search_by_passports(self.stable_key_to_sections)
            if section_id is not None:
                row[id_index] = str("section-") + str(section_id)
            else:
                raise ConvertException("cannot find in disclosures declarator section_id={}, passport={}, "
                                       "search_results={} ".format(
                    section_or_person_id,
                    passport_factory.get_passport_collection()[0],
                    search_results))

    def handle(self, *args, **options):
        output_lines = list()
        header = list()
        self.log("start conversion ...")
        with open(options['input_pool'], "r") as tsv:
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
                        self.convert_line(header, 'INPUT:id_left', 'INPUT:json_left', task_row)
                        self.convert_line(header, 'INPUT:id_right', 'INPUT:json_right', task_row)
                    output_lines.append(task_row)
                    good_lines += 1
                except (ConvertException, models.Person.DoesNotExist) as exp:
                    self.log("Line: {}, Exception: {}, continue\n".format(row_index, exp))
            self.log("converted {} lines out of {} lines".format(good_lines, row_index))
        with open(options['output_pool'], 'w') as out_file:
            tsv_writer = csv.writer(out_file, delimiter="\t")
            tsv_writer.writerow(header)
            for row in output_lines:
                tsv_writer.writerow(row)


