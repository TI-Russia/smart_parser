import pickle
import csv
import json
import os
from collections import defaultdict
from deduplicate.toloka import TToloka
from django.core.management import BaseCommand
import declarations.models as models
import django.db.utils
from declarations.common import resolve_fullname
from declarations.rubrics import get_russian_rubric_str
from declarations.serializers import get_section_json
import random
import logging


def setup_logging(logfilename="new_toloka_tasks.log"):
    logger = logging.getLogger("toloka")
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
    person_coeff = +1  # there is no person.id == 0, so all person ids ar positive and all section ids are negative or zero
    section_coeff = -1

    def __init__(self, logger):
        self.logger = logger
        self.office_info = dict()
        self.surname_rank = dict()
        self.id_list = list()
        self.id_cum_weights = list()

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
        self.office_info.clear()
        sql = """select o.id, o.name, count(s.id) as section_count
                  from declarations_office o 
                  join declarations_source_document d on d.office_id = o.id 
                  join declarations_section s on s.source_document_id = d.id 
                  group by o.id
              """
        self.logger.info("build offices")
        for o in models.Office.objects.raw(sql):
            self.office_info[o.id] = {"section_count": o.section_count}
        self.logger.info("office count = {}".format(len(self.office_info)))

    def build_persons(self, surname_to_unified_ids):
        self.logger.info("build persons")
        sql = 'SELECT id, person_name FROM declarations_person where declarator_person_id is not null'
        cnt = 0
        for p in models.Person.objects.raw(sql):
            fio = resolve_fullname(p.person_name)
            if fio is not None:
                surname = fio['family_name'].lower()
                surname_to_unified_ids[surname].append(TDBSqueeze.person_coeff * p.id)
                cnt += 1
        self.logger.info("persons count = {}".format(cnt))

    def build_sections_and_surname_rank(self, surname_to_unified_ids):
        self.surname_rank.clear()
        surname_to_initials = defaultdict(set)
        sql = """
                select s.id as id, s.person_name as person_name  
                from declarations_section s 
                join declarations_income i on i.section_id = s.id
                where i.relative = "{}"
            """.format(models.Relative.main_declarant_code)
        self.logger.info("build sections")
        cnt = 0
        for s in models.Section.objects.raw(sql):
            fio = resolve_fullname(s.person_name)
            if fio is not None:
                surname = fio['family_name'].lower()
                surname_to_unified_ids[surname].append(TDBSqueeze.section_coeff * s.id)
                initials = "{} {}".format(fio.get('name', " ")[0].lower(), fio.get('patronymic', " ")[0].lower())
                surname_to_initials[surname].add(initials)
                cnt += 1
        self.logger.info("sections count = {}".format(cnt))

        surname_rank_list = sorted(((len(v), k) for k, v in surname_to_initials.items()), reverse=True)
        self.surname_rank = list(surname for freq, surname in surname_rank_list)
        self.logger.info("surname count = {}".format(len(self.surname_rank)))

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
        self.build_sections_and_surname_rank(surname_to_unified_ids)
        self.build_id_list(surname_to_unified_ids)


def get_section_year(s):
    return int(s.get('years', s['year']))



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

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging()
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
        fio1 = resolve_fullname(rec1.person_name)
        fio2 = resolve_fullname(rec2.person_name)
        assert fio1 is not None and fio2 is not None
        assert fio1['family_name'].lower() == fio2['family_name'].lower()
        if not are_compatible_Russian_fios(fio1, fio2):
            self.logger.debug('auto negative example {} and {} because fio are not compatible'.format(rec1.person_name,
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

            self.logger.debug(
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

    def build_section_json_for_toloka(self, section_sql_records):
        surname = resolve_fullname(section_sql_records[0].person_name)['family_name'].lower()
        surname_rank = self.db_squeeze.surname_rank.index(surname)
        sections = list()
        for s in section_sql_records:
            section_json = get_section_json(s)
            office_id = section_json['office_id']
            section_json['office_section_count'] = self.db_squeeze.office_info[office_id]['section_count']
            office = models.Office.objects.get(id=office_id)
            section_json['office_rubric'] = get_russian_rubric_str(office.rubric_id)
            section_json['office_region'] = self.region_id_to_name.get(office.region_id, "")
            section_json['surname_rank'] = surname_rank
            sections.append(section_json)
        return {'sections': sections}

    def add_task_line(self, id1, id2, golden_result, tasks):
        rec1 = self.create_record(id1)
        rec2 = self.create_record(id2)

        if (self.check_auto_negative_fio(rec1, rec2) or
                self.check_auto_negative_office(rec1, rec2)):
            return False

        sections1 = self.get_sections(rec1)
        sections2 = self.get_sections(rec2)
        if len(set(sections1).intersection(set(sections2))) > 0:
            self.logger.debug("{} and {} have at least one section in common, ignore it".format(id1, id2))
            return False

        p1_json = self.build_section_json_for_toloka(sections1)
        p2_json = self.build_section_json_for_toloka(sections2)

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

    def generate_pairs(self):
        while True:
            for id1 in random.choices(self.db_squeeze.id_list, cum_weights=self.db_squeeze.id_cum_weights, k=100):
                index1 = self.db_squeeze.id_list.index(id1)
                index2_start = index1 + 1
                index2_end = index2_start + self.db_squeeze.get_ordered_pairs_count(index1)
                id2 = random.choice(self.db_squeeze.id_list[index2_start:index2_end])
                assert id1 < id2
                # do not yield (person, person)
                if not self.db_squeeze.unified_id_is_section(id1) and not self.db_squeeze.unified_id_is_section(id2):
                    continue
                yield TDBSqueeze.id_to_str(id1), TDBSqueeze.id_to_str(id2)

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
        tasks = TolokaTasks()

        for id1, id2 in self.generate_pairs():
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
        self.logger.info('All tasks count in result TSV: {}'.format(len(tasks.output_lines)))
        self.logger.info('Golden Set tasks count in result TSV: {}'.format(golden_count))
        self.logger.info(
            'Auto positive examples (not written to the result file): {}'.format(len(tasks.auto_positive_examples)))
        self.logger.info(
            'Auto negative examples (not written to the result file): {}'.format(len(tasks.auto_negative_examples)))
        self.logger.info('Export to TSV completed, do not forget to add new pools {} to the repository.'.format(
            output_file_name))

    def handle(self, *args, **options):
        self.logger.info('Started')
        if options['action'] == "prepare":
            self.prepare_data()
            return

        self.load_data(options)
        self.new_toloka_tasks(
            task_count=options.get('pairs_amount'),
            golden_set_ratio=options.get('goldenset_ratio'),
            pool_name=options['output_name'],
            goldensets=self.get_golden_examples(options['goldenset_file'])
        )

