from common.logging_wrapper import setup_logging
from deduplicate.toloka import TToloka
from declarations.russian_fio import TRussianFio
from declarations.rubrics import get_russian_rubric_str
from declarations.serializers import get_section_json
import declarations.models as models

import pickle
import csv
import json
import os
from collections import defaultdict
from django.core.management import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
import django.db.utils
import random
import logging


class TDBSqueeze:
    person_coeff = +1  # there is no person.id == 0, so all person ids ar positive and all section ids are negative or zero
    section_coeff = -1

    def __init__(self, logger):
        self.logger = logger
        self.office_info = dict()
        self.surname_rank = dict()
        self.id_list = list()
        self.id_cum_weights = list() #random.choice takes cum_weights to create a weighted sample

    @staticmethod
    def unified_id_is_section(id):
        return id <= 0

    @staticmethod
    def unified_id_to_sql_id(id):
        if TDBSqueeze.unified_id_is_section(id):
            return int(id / TDBSqueeze.section_coeff)
        else:
            return int(id / TDBSqueeze.person_coeff)

    @staticmethod
    def id_to_str(id):
        if TDBSqueeze.unified_id_is_section(id):
            return "section-{}".format(TDBSqueeze.unified_id_to_sql_id(id))
        else:
            return "person-{}".format(TDBSqueeze.unified_id_to_sql_id(id))

    def get_ordered_pairs_count(self, index1):
        if index1 == 0:
            return self.id_cum_weights[0]
        else:
            return self.id_cum_weights[index1] - self.id_cum_weights[index1 - 1]

    def build_office_stats(self):
        """  build section count for tolokers (just additional iuformation) """
        self.office_info.clear()
        sql = """select o.id, o.name, count(s.id) as section_count
                  from declarations_office o 
                  join declarations_source_document d on d.office_id = o.id 
                  join declarations_section s on s.source_document_id = d.id 
                  group by o.id
              """
        self.logger.info("build web_site_snapshots")
        for o in models.Office.objects.raw(sql):
            self.office_info[o.id] = {"section_count": o.section_count}
        self.logger.info("office count = {}".format(len(self.office_info)))

    def build_persons(self, surname_to_unified_ids):
        self.logger.info("build surname -> person.id  ")
        sql = 'SELECT id, person_name FROM declarations_person where declarator_person_id is not null'
        cnt = 0
        for p in models.Person.objects.raw(sql):
            fio = TRussianFio(p.person_name)
            if fio.is_resolved:
                surname_to_unified_ids[fio.family_name].append(TDBSqueeze.person_coeff * p.id)
                cnt += 1
        self.logger.info("persons count = {}".format(cnt))

    def build_sections(self, surname_to_unified_ids):
        self.logger.info("build surname -> section.id  ")
        sql = """
                select s.id as id, s.person_name as person_name  
                from declarations_section s 
                join declarations_income i on i.section_id = s.id
                where i.relative = "{}"
            """.format(models.Relative.main_declarant_code)
        self.logger.info("build sections")
        cnt = 0
        for s in models.Section.objects.raw(sql):
            fio = TRussianFio(s.person_name)
            if fio.is_resolved:
                surname_to_unified_ids[fio.family_name].append(TDBSqueeze.section_coeff * s.id)
                cnt += 1
        self.logger.info("sections count = {}".format(cnt))

    def build_id_list(self, surname_to_unified_ids):
        self.logger.info("build id list")
        self.id_list = list()
        self.id_cum_weights = list()
        cum_weight = 0
        for surname, id_list in surname_to_unified_ids.items():
            id_list.sort()
            for i in range(len(id_list)):
                self.id_list.append(id_list[i])
                ordered_pairs_count = len(id_list) - i - 1
                cum_weight += ordered_pairs_count
                self.id_cum_weights.append(cum_weight)
        self.logger.info("save info about {} pairs".format(cum_weight))

    def build(self):
        self.build_office_stats()
        surname_to_unified_ids = defaultdict(list)
        self.build_persons(surname_to_unified_ids)
        self.build_sections(surname_to_unified_ids)
        self.build_id_list(surname_to_unified_ids)

    def generate_pairs(self):
        while True:
            for id1 in random.choices(self.id_list, cum_weights=self.id_cum_weights, k=100):
                index1 = self.id_list.index(id1)
                index2_start = index1 + 1
                index2_end = index2_start + self.get_ordered_pairs_count(index1)
                id2 = random.choice(self.id_list[index2_start:index2_end])
                assert id1 < id2
                # do not yield (person, person)
                if not self.unified_id_is_section(id1) and not self.unified_id_is_section(id2):
                    continue
                yield self.id_to_str(id1), self.id_to_str(id2)


def get_section_year(s):
    return int(s.get('years', s['year']))


class TOneTask:
    verdict_yes = "YES"
    verdict_no = "NO"
    verdict_unknown = "UNK"

    def __init__(self, id_left, id_right, json_left=None, json_right=None, verdict=None):
        self.id_left = id_left
        self.id_right = id_right
        self.json_left = json_left
        self.json_left_str = json.dumps(json_left, ensure_ascii=False)
        self.json_right = json_right
        self.json_right_str = json.dumps(json_right, ensure_ascii=False)
        self.golden = ""

        if self.json_left_str == self.json_right_str:
            # no difference in data, no sense to show it to tolokers
            self.verdict = TOneTask.verdict_yes
        else:
            self.verdict = verdict
            if self.verdict is None:
                self.verdict = TOneTask.verdict_unknown



class Command(BaseCommand):
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
        parser.add_argument(
            '--pool-to-test-auto-negative',
            dest='pool_to_test_auto_negative',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(log_file_name="new_toloka_tasks.log")
        self.db_squeeze = TDBSqueeze(self.logger)
        self.db_squeeze_pickled_file_path = "squeeze.pickle"
        self.region_id_to_name = self.read_regions()

    def read_regions(self):
        region_id_to_name = dict()
        for r in models.Region_Synonyms.objects.all():
            if r.synonym_class == models.SynonymClass.Russian:
                region_id_to_name[r.region_id] = r.synonym
            if r.synonym_class == models.SynonymClass.RussianShort and r.region_id not in region_id_to_name:
                region_id_to_name[r.region_id] = r.synonym
        self.logger.debug("read {} regions".format(len(region_id_to_name)))
        return region_id_to_name

    def prepare_data(self):
        self.logger.info("Serializing from DB...")
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
        self.logger.info("read {} previous task files, all previous tasks count = {} ".format(file_count, len(result)))
        return result

    def get_golden_examples(self, filename):
        if filename is None:
            self.logger.error("no goldenset provided, these tasks cannot be processed by read tolokers")
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
            self.logger.error("cannot create record by {}, probably it was deleted ".format(string_id))
            raise e

    def check_auto_negative_fio(self, rec1, rec2):
        fio1 = TRussianFio(rec1.person_name)
        fio2 = TRussianFio(rec2.person_name)
        assert fio1.is_resolved and fio2.is_resolved
        assert fio1.family_name == fio2.family_name
        if not fio1.is_compatible_to(fio2):
            self.logger.debug('auto negative example {} and {} because fio are not compatible'.format(rec1.person_name,
                                                                                              rec2.person_name))
            return True
        return False

    def check_auto_negative_freq_fio(self, rec1, rec2):
        if isinstance(rec1, models.Section) and isinstance(rec2, models.Section):
            if rec1.surname_rank < 300 and (rec1.name_rank < 200 or rec2.name_rank < 200):
                if rec1.source_document.office.rubric_id != rec2.source_document.office.rubric_id:
                    self.logger.debug("section {} and secion {} ({}) are filtered out by "
                                      "rule check_auto_negative_freq_fio".format(
                        rec1.id, rec2.id, rec1.person_name))
                    return True
        return False

    def get_sections(self, record):
        if isinstance(record, models.Person):
            return list(record.section_set.all())
        else:
            return [record]

    def build_section_json_for_toloka(self, section_sql_records):
        sections = list()
        for s in section_sql_records:
            section_json = get_section_json(s)
            office_id = section_json['office_id']
            section_json['office_section_count'] = self.db_squeeze.office_info[office_id]['section_count']
            office = models.Office.objects.get(id=office_id)
            section_json['office_rubric'] = get_russian_rubric_str(office.rubric_id)
            section_json['office_region'] = self.region_id_to_name.get(office.region_id, "")
            section_json['surname_rank'] = s.surname_rank
            section_json['name_rank'] = s.name_rank
            sections.append(section_json)
        return {'sections': sections}

    def get_one_task(self, id1, id2):
        rec1 = self.create_record(id1)
        rec2 = self.create_record(id2)
        sections1 = self.get_sections(rec1)
        sections2 = self.get_sections(rec2)
        p1_json = self.build_section_json_for_toloka(sections1)
        p2_json = self.build_section_json_for_toloka(sections2)
        id1, id2, p1_json, p2_json = self.__sort_left_right_json_data(id1, id2, p1_json, p2_json)
        task = TOneTask(id1, id2, p1_json, p2_json)

        if (self.check_auto_negative_fio(rec1, rec2) or
                self.check_auto_negative_freq_fio(rec1, rec2)):
            task.verdict = TOneTask.verdict_no

        if len(set(sections1).intersection(set(sections2))) > 0:
            self.logger.debug("{} and {} have at least one section in common, ignore it".format(id1, id2))
            task.verdict = TOneTask.verdict_no
        return task

    def new_toloka_tasks(self, task_count, golden_set_ratio, pool_name, goldensets):
        gs_task_count = int(task_count * golden_set_ratio)
        output_file_name = os.path.join(TToloka.TASKS_PATH, pool_name)
        self.logger.info('task_count = {}'.format(task_count))
        self.logger.info('golden tasks to be found = {}'.format(gs_task_count))
        prev_tasks = self.read_previous_tasks()
        if output_file_name.endswith('.tsv'):
            output_file_name = output_file_name[0:-4]
        output_file_name = output_file_name + ".tsv"
        self.logger.info('create file  = {}'.format(output_file_name))
        tasks = list()
        auto_negative_count = 0
        auto_positive_count = 0
        for id1, id2 in self.db_squeeze.generate_pairs():
            if (id1, id2) in prev_tasks or (id2, id1) in prev_tasks:
                continue
            task = self.get_one_task(id1, id2)
            if task.verdict == TOneTask.verdict_unknown:
                tasks.append(task)
                if len(tasks) >= task_count:
                    break
            elif task.verdict == TOneTask.verdict_yes:
                auto_positive_count += 1
            else:
                auto_negative_count += 1

        golden_count = 0
        for id1, id2, golden_result in goldensets:
            try:
                task = self.get_one_task(id1, id2)
                task.golden = golden_result
                if task.verdict == TOneTask.verdict_unknown:
                    tasks.append(task) # old golden tasks can banned by new auto rules
                    golden_count += 1
                if golden_count >= gs_task_count:
                    break
            except django.db.utils.IntegrityError as err:
                pass
            except ObjectDoesNotExist as err:
                pass

        #if golden_count < gs_task_count:
        #    raise Exception("cannot find  enough golden-set examples found {0}, must be at least {1}".format(golden_count,gs_task_count))

        with open(output_file_name, 'w') as out_file:
            header = [TToloka.ID_LEFT, TToloka.ID_RIGHT,
                      TToloka.JSON_LEFT, TToloka.JSON_RIGHT, TToloka.GOLDEN]
            tsv_writer = csv.writer(out_file, delimiter="\t")
            tsv_writer.writerow(header)
            random.shuffle(tasks)  # do not delete it, you can easily forget it in toloka interface
            for t in tasks:
                tsv_writer.writerow([t.id_left, t.id_right, t.json_left_str, t.json_right_str, t.golden])

        self.logger.info('All tasks count in result TSV: {}'.format(len(tasks)))
        self.logger.info('Golden Set tasks count in result TSV: {}'.format(golden_count))
        self.logger.info('Auto positive examples (not written to the result file): {}'.format(auto_positive_count))
        self.logger.info('Auto negative examples (not written to the result file): {}'.format(auto_negative_count))
        self.logger.info('Export to TSV completed, do not forget to add new pools {} to the repository.'.format(
            output_file_name))

    def apply_auto_negative_rules(self, test_pool_path):
        test_data = TToloka.read_toloka_golden_pool(test_pool_path)
        self.logger.info("check {} cases".format(len(list(test_data.items()))))
        tn = 0
        fn = 0
        for ((id1, id2), mark) in test_data.items():
            task = self.get_one_task(id1, id2)
            if task.verdict == TOneTask.verdict_unknown:
                surname_rank = task.json_left['sections'][0]['surname_rank']
                name_rank = task.json_left['sections'][0]['name_rank']
                rubric_left = set(s['office_rubric'] for s in task.json_left['sections'])
                rubric_right = set(s['office_rubric'] for s in task.json_right['sections'])
                if surname_rank < 300 and name_rank < 200:
                    if len(rubric_left.intersection(rubric_right)) == 0:
                        if mark != "NO":
                            self.logger.info("false negative: {} {}".format(id1, id2))
                            fn += 1
                        else:
                            self.logger.info("true negative: {} {}".format(id1, id2))
                            tn +=1

        self.logger.info("true negative = {}, false negative = {}".format(tn, fn))

    def handle(self, *args, **options):
        self.logger.info('Started')
        if options['action'] == "prepare":
            self.prepare_data()
            return

        self.load_data(options)
        if options.get('pool_to_test_auto_negative') is not None:
            self.apply_auto_negative_rules(options.get('pool_to_test_auto_negative'))
        else:
            self.new_toloka_tasks(
                task_count=options.get('pairs_amount'),
                golden_set_ratio=options.get('goldenset_ratio'),
                pool_name=options['output_name'],
                goldensets=self.get_golden_examples(options['goldenset_file'])
            )

