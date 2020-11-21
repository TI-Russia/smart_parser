# -*- coding: utf-8 -*-
import pickle
import csv
import json
import os
from collections import defaultdict
import Levenshtein
from datetime import datetime
from deduplicate.toloka import TToloka
from django.core.management import BaseCommand
import declarations.models as models
import django.db.utils
from declarations.common import resolve_fullname
from declarations.serializers import get_section_json
import random


# Жуков Иван Николаевич	Жуков И Н -> true
# Жуков И Н	Жуков И Н -> true
# Жуков И П	Жуков И Н -> false
# Жуков Иван П	Жуков Исаак Н -> false

def are_compatible_Russian_fios(fio1, fio2):
    f1, i1, o1 = fio1['family_name'], fio1['name'], fio1['patronymic']
    f2, i2, o2 = fio2['family_name'], fio2['name'], fio2['patronymic']
    return (f1 == f2 and
            ((i1.startswith(i2) and o1.startswith(o2))
             or (i2.startswith(i1) and o2.startswith(o1))
             )
            )


class TolokaTasks:
    def __init__(self):
        self.output_lines = []
        self.auto_negative_examples = []
        self.auto_positive_examples = []


class TDBSqueeze:
    def __init__(self):
        self.persons = None
        self.sections = None

    def build_persons(self):
        persons = defaultdict(list)
        for p in models.Person.objects.raw('SELECT id, person_name FROM declarations_person where declarator_person_id is not null'):
            fio = resolve_fullname(p.person_name)
            if fio is not None:
                persons[fio['family_name']].append(p.id)
        return persons

    def build_sections(self):
        sections = defaultdict(list)
        for s in models.Section.objects.raw('SELECT id, person_name FROM declarations_section'):
            fio = resolve_fullname(s.person_name)
            if fio is not None:
                sections[fio['family_name']].append(s.id)
        return sections

    def build(self):
        self.persons = self.build_persons()
        self.sections = self.build_sections()


def get_section_year(s):
    return int(s.get('years', s['year']))

class Command(BaseCommand):
    """
    Создание пар для толоки.
    Фильтрованные записи из базы => в TSV

    """

    help = 'Создание пар для толоки'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            dest='action',
            default="import",
            required=False,
            help="can be prepare or generate",
        )
        parser.add_argument(
            '--output-name',
            dest='output_name',
            help='pool name to generate in {}'.format(TToloka.TASKS_PATH)
        )
        parser.add_argument(
            '--goldenset-ratio',
            dest='goldenset_ratio',
            type=float,
            default=0.1,
            help='Ratio of golden set pairs within the pool [0.0 - 1.0]',
        )
        parser.add_argument(
            '--goldenset-file',
            dest='goldenset_file',
            default=None,
            help='golden set examples',
        )
        parser.add_argument(
            '--pairs-amount',
            dest='pairs_amount',
            type=int,
            default=100,
            help='Total amount of pairs in TSV',
        )
        parser.add_argument(
            '--office-id',
            nargs='+',
            dest='office_id',
            help='section office id (can me many)',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.db_squeeze = TDBSqueeze()
        self.db_squeeze_pickled_file_path = "squeeze.pickle"

    def log(self, msg):
        self.stdout.write('{}'.format(datetime.now()) + (' - ' + msg) if msg else '')

    def prepare_data(self):
        self.log("Serializing from DB...")
        self.db_squeeze.build()
        with open(self.db_squeeze_pickled_file_path, 'wb') as f:
            pickle.dump(self.db_squeeze, f)

    def load_data(self, options):
        if not os.path.exists(self.db_squeeze_pickled_file_path):
            raise RuntimeError("run  python3 manage.py new_toloka_tasks --action prepare --settings disclosures.settings.prod")
        with open(self.db_squeeze_pickled_file_path, 'rb') as f:
            self.db_squeeze = pickle.load(f)

    def read_previous_tasks(self):
        result = set()
        file_count = 0
        for f in os.listdir(TToloka.TASKS_PATH):
            filename = os.path.join(TToloka.TASKS_PATH, f)
            if filename.endswith('.tsv'):
                file_count += 1
                for line in csv.DictReader(open(filename), delimiter="\t"):
                    pair = (line[TToloka.ID_LEFT], line[TToloka.ID_RIGHT])
                    result.add(pair)
        self.log("read {} previous task files, all previous tasks count = {} ".format(file_count, len(result)))
        return result

    def get_golden_examples(self, filename):
        if filename is None:
            self.log("no goldenset provided, these tasks cannot be processed by read tolokers")
            return []
        result = []
        for line in csv.DictReader(open(filename), delimiter="\t"):
            result.append((line[TToloka.ID_LEFT], line[TToloka.ID_RIGHT], line[TToloka.GOLDEN]))
        random.shuffle(result)
        return result

    def __sort_left_right_json_data(self, left_uid, right_uid, left_json, right_json):
        """
        Sort `left` and `right` json data using `section`.`years` field values
        """
        min_left = min(get_section_year(s) for s in left_json['sections'])
        min_right = min(get_section_year(s) for s in right_json['sections'])

        if min_left > min_right:
            # self.log('Swapping left {} with right {} because of'.format(left_uid, right_uid) +
            #    ' years unsorted ({}, {})'.format(min_left, min_right))
            # if min_year(left) < min_year(left) than swap!

            return right_uid, left_uid, right_json, left_json
        else:
            return left_uid, right_uid, left_json, right_json

    def create_record(self, string_id):
        try:
            if string_id.startswith("section-"):
                id = int(string_id[len("section-"):])
                return models.Section.objects.get(id=id)
            elif string_id.startswith("person-"):
                id = int(string_id[len("person-"):])
                return models.Person.objects.get(id=id)
            else:
                assert (False)
        except django.db.utils.IntegrityError as e:
            self.log("cannot create record by {}, probably it was deleted ".format(string_id))
            raise e

    def check_auto_negative_fio(self, rec1, rec2):
        fio1 = resolve_fullname(rec1.person_name)
        fio2 = resolve_fullname(rec2.person_name)

        if fio1 is None or fio2 is None:
            # not normal Russian FIOs
            if Levenshtein.ratio(rec1.person_name, rec2.person_name) < 0.9:
                self.log(u'auto negative example {} and {} because levenshtein < 0.9'.format(rec1.person_name,
                                                                                             rec2.person_name))
                return True
        else:
            if not are_compatible_Russian_fios(fio1, fio2):
                self.log(u'auto negative example {} and {} because fio are not compatible'.format(rec1.person_name,
                                                                                                  rec2.person_name))
                return True
        return False

    # one year, one office, one fio, different incomes -> different people
    def check_auto_negative_office(self, rec1, rec2):
        try:
            if rec1.person_name != rec2.person_name:
                return False
            sections1 = rec1.get_sections()
            sections2 = rec2.get_sections()
            if len(sections1) != 1 or len(sections2) != 1:
                return False

            if sections1[0].document.income_year != sections2[0].document.income_year:
                return False

            if sections1[0].document.office.name != sections2[0].document.office.name:
                return False

            income1 = int(sections1[0].income_set.filter(relative=None).first().size / 100)
            income2 = int(sections2[0].income_set.filter(relative=None).first().size / 100)
            if income1 == income2:
                return False

            self.log(
                'auto negative example {}, incomes {}  and {} one year, one office, one fio, different incomes -> different people'.format(
                    rec1.person_name,
                    income1,
                    income2))
        except:
            return False  # no incomes

    def get_sections(self, record):
        if isinstance(record, models.Person):
            return list(record.section_set.all())
        else:
            return [record]

    def add_task_line(self, id1, id2, golden_result, tasks):
        rec1 = self.create_record(id1)
        rec2 = self.create_record(id2)

        if (self.check_auto_negative_fio(rec1, rec2) or
                self.check_auto_negative_office(rec1, rec2)):
            if id1 > id2:
                id1, id2 = id2, id1
            if golden_result != "":
                tasks.auto_negative_examples.append([id1, id2, "NO"])
            return False

        sections1 = self.get_sections(rec1)
        sections2 = self.get_sections(rec2)
        if len(set(sections1).intersection(set(sections2))) > 0:
            self.log("{} and {} have at least one section in common, ignore it".format(id1, id2))
            return False

        p1_json = {'sections': list(get_section_json(s) for s in sections1)}
        p2_json = {'sections': list(get_section_json(s) for s in sections2)}

        id1, id2, p1_json, p2_json = self.__sort_left_right_json_data(id1, id2, p1_json, p2_json)
        js1 = json.dumps(p1_json, ensure_ascii=False)
        js2 = json.dumps(p2_json, ensure_ascii=False)

        if js1 == js2:
            # no difference in data, no sense to show it to tolokers
            tasks.auto_positive_examples.append([id1, id2, "YES"])
            return False

        row = [
            id1,
            id2,
            js1,
            js2,
            golden_result
        ]

        tasks.output_lines.append(row)
        return True

    def new_toloka_tasks(self, pairs, task_count, golden_set_ratio, pool_name, goldensets):
        gs_task_count = int(task_count * golden_set_ratio)
        output_file_name = os.path.join(TToloka.TASKS_PATH, pool_name)
        self.log('-' * 79)
        self.log('  task_count = {}'.format(task_count))
        self.log('  golden tasks to be found = {}'.format(gs_task_count))

        prev_tasks = self.read_previous_tasks()
        if output_file_name.endswith('.tsv'):
            output_file_name = output_file_name[0:-4]
        auto_output_file_name = output_file_name + "_auto.tsv"
        output_file_name = output_file_name + ".tsv"
        self.log('  create file  = {}'.format(output_file_name))
        self.log('  create file  = {}'.format(auto_output_file_name))
        tasks = TolokaTasks()

        for id1, id2 in pairs:
            if (id1, id2) in prev_tasks or (id2, id1) in prev_tasks:
                continue
            self.add_task_line(id1, id2, "", tasks)
            if len(tasks.output_lines) >= task_count:
                break

        golden_count = 0
        for id1, id2, golden_result in goldensets:
            added = False
            try:
                added = self.add_task_line(id1, id2, golden_result, tasks)
            except django.db.utils.IntegrityError as err:
                pass

            if added:
                golden_count += 1
                if golden_count >= gs_task_count:
                    break

        #if golden_count < gs_task_count:
        #    raise Exception("cannot find  enough golden-set examples found {0}, must be at least {1}".format(golden_count,gs_task_count))

        with open(output_file_name, 'w') as out_file:
            header = [TToloka.ID_LEFT, TToloka.ID_RIGHT,
                      TToloka.JSON_LEFT, TToloka.JSON_RIGHT, TToloka.GOLDEN]
            tsv_writer = csv.writer(out_file, delimiter="\t")
            tsv_writer.writerow(header)
            random.shuffle(tasks.output_lines)  # do not delete it, you can easily forget it in toloka interface
            for row in tasks.output_lines:
                tsv_writer.writerow(row)

        with open(auto_output_file_name, 'w') as out_file:
            tsv_writer = csv.writer(out_file, delimiter="\t")
            tsv_writer.writerow([TToloka.ID_LEFT, TToloka.ID_RIGHT, TToloka.GOLDEN])
            for row in tasks.auto_negative_examples:
                tsv_writer.writerow(row)

        print('TSV results:')
        print('All tasks count in result TSV: {}'.format(len(tasks.output_lines)))
        print('Golden Set tasks count in result TSV: {}'.format(golden_count))
        print(
            'Auto positive examples (not written to the result file): {}'.format(len(tasks.auto_positive_examples)))
        print(
            'Auto negative examples (not written to the result file): {}'.format(len(tasks.auto_negative_examples)))
        self.log('Export to TSV completed, do not forget to add new pools {} and {} to the repository.'.format(
            output_file_name, auto_output_file_name))

    def handle(self, *args, **options):
        self.log('Started')
        if options['action'] == "prepare":
            self.prepare_data()
            return

        self.load_data(options)
        pairs = list()
        for key in random.choices(list(self.db_squeeze.sections.keys()), k=500):
            ids = list("section-{0}".format(id) for id in self.db_squeeze.sections[key])
            ids.extend(list("person-{0}".format(id) for id in self.db_squeeze.persons[key]))
            ids = random.choices(ids, k=80)
            for id1 in ids:
                for id2 in ids:
                    if id1 < id2:
                        if id1.startswith('section-') or id2.startswith('section-'):
                            pairs.append((id1, id2))
        random.shuffle(pairs)
        self.new_toloka_tasks(
            pairs,
            task_count=options.get('pairs_amount'),
            golden_set_ratio=options.get('goldenset_ratio'),
            pool_name=options['output_name'],
            goldensets=self.get_golden_examples(options['goldenset_file'])
        )
