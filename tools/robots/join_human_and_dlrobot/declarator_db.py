import pymysql
import os
import re
import json
from collections import defaultdict


def normalize_whitespace(str):
    str = re.sub(r'\s+', ' ', str)
    str = str.strip()
    return str


def build_office_domains(dlrobot_human_file_info):
    offices_to_domains = defaultdict(list)
    for domain in dlrobot_human_file_info:
        offices = list(x['office_id'] for x in dlrobot_human_file_info[domain].values() if 'office_id' in x)
        if len(offices) == 0:
            raise Exception("no office found for domain {}".format(domain))
        most_freq_office = max(set(offices), key=offices.count)
        offices_to_domains[most_freq_office].append(domain)
    return offices_to_domains


def get_document_file_id(file_info):
    file_id = os.path.splitext(os.path.basename(file_info['filepath']))[0]
    if file_id.find('_') != -1:
        file_id = file_id[0:file_id.find('_')]
    return int(file_id)


def get_smart_parser_results(input_path):
    if not os.path.exists(input_path):
        # todo: why ?
        print("Error! cannot find {}, though it is in dlrobot_human.json".format(input_path))
        return

    if os.path.exists(input_path + ".json"):
        yield input_path + ".json"
    else:
        index = 0
        while True:
            filename = input_path + "_{}.json".format(index)
            if not os.path.exists(filename):
                break
            yield filename
            index += 1


def get_declarant_income(p):
    for i in p.get('incomes', []):
        if i.get('relative') is None:
            declarant_income = i.get('size', "null")
            if isinstance(declarant_income, float):
                return int(declarant_income)
            if declarant_income.isdigit():
                return int(declarant_income)
            return declarant_income


def build_stable_section_id_1(fio, income, year, document_id):
    fio = normalize_whitespace(fio).lower()
    if income is None:
        income = 0
    if year is None:
        year = 0
    return "\t".join([fio, str(int(income)), str(year), str(document_id)])


def build_stable_section_id_2(fio, income, year, document_id):
    fio = normalize_whitespace(fio).lower()
    if len(fio) > 0:
        fio = fio.split(" ")[0]  # only family_name
    if income is None:
        income = 0
    if year is None:
        year = 0
    return "\t".join([fio, str(int(income)), str(year), str(document_id)])


class TDeclaratorDBSqueezes:

    def init_offices(self):
        in_cursor = self.declarator_db_connection.cursor()
        in_cursor.execute("select id, name from declarations_office")
        self.office_names = dict((id, name) for id, name in in_cursor)
        in_cursor.close()

    def init_file_2_documents(self):
        in_cursor = self.declarator_db_connection.cursor()
        in_cursor.execute("select id, document_id from declarations_documentfile")
        self.file_2_document = dict(x for x in in_cursor)
        for file_id, document_id in self.file_2_document.items():
            self.document_2_files[document_id].add(file_id)

        in_cursor.execute("select id, name from declarations_office")
        self.office_names = dict((id, name) for id, name in in_cursor)
        in_cursor.close()

    def get_section_incomes(self):
        in_cursor = self.declarator_db_connection.cursor()
        in_cursor.execute("select section_id, size from declarations_income where relative_id is null")
        res = dict(x for x in in_cursor)
        in_cursor.close()
        return res

    def get_mapping_section_to_stable_id(self):
        in_cursor = self.declarator_db_connection.cursor()
        in_cursor.execute("""
                        select  s.id, 
                                s.person_id, 
                                s.document_id, 
                                s.original_fio, 
                                CONCAT(p.family_name, " ", p.name, " ", p.patronymic),
                                d.income_year
                        from declarations_section s
                        inner join declarations_person p on p.id = s.person_id
                        inner join declarations_document d on s.document_id = d.id
                        where s.person_id is not null
        """)

        incomes = self.get_section_incomes()
        human_persons = dict()
        human_section_mergings_count = 0
        for section_id, person_id, document_id, original_fio, person_fio, year in in_cursor:
            fio = original_fio
            if fio is None:
                fio = person_fio
            assert fio is not None
            key1 = build_stable_section_id_1(fio, incomes.get(section_id, 0), year, document_id)
            if key1 not in human_persons:
                human_persons[key1] = person_id
            else:
                human_persons[key1] = None

            key2 = build_stable_section_id_2(fio, incomes.get(section_id, 0), year, document_id)
            if key2 not in human_persons:
                human_persons[key2] = person_id
            else:
                human_persons[key2] = None
            human_section_mergings_count += 1

        in_cursor.close()
        print("found {} sections with some person_id != null in declarator db".format(human_section_mergings_count))
        return human_persons

    def _copy_human_merges(self, sha256_to_human_file, human_persons, dlrobot_db):
        dlrobot_section_id_to_person_id = dict()
        used_stable_ids = set()
        for dlrobot_section_id, fio, income_year, declarant_income, source_file_sha256, document_id in dlrobot_db.iterate_all_sections():
            if document_id is None:
                file_id = sha256_to_human_file.get(source_file_sha256)
                if file_id is None:
                    continue  # a file that is not in declarator db
                document_id = self.file_2_document.get(file_id)
                if document_id is None:
                    continue  # unknown cause

            key1 = build_stable_section_id_1(fio, declarant_income, income_year, document_id)
            key2 = build_stable_section_id_2(fio, declarant_income, income_year, document_id)
            person_id = human_persons.get(key1)
            if person_id is None:
                person_id = human_persons.get(key2)

            if person_id is not None:
                dlrobot_section_id_to_person_id[dlrobot_section_id] = person_id
                used_stable_ids.add(key1)
                used_stable_ids.add(key2)


        missing_set = set(k for k, v in human_persons.items() if v is not None) - used_stable_ids
        print(
            "there are {} human merged sections that were not found in dlrobot db (smart_parser parsed files with errors?)".format(
                len(missing_set)))

        mergings_count = 0
        cursor = dlrobot_db.get_new_output_cursor()
        for id, person_id in dlrobot_section_id_to_person_id.items():
            dlrobot_db.update_person_id(cursor, id, person_id)
            mergings_count += 1
        dlrobot_db.close_output_cursor_and_commit(cursor)
        print("set human person id to {} records".format(mergings_count))

    def copy_human_section_merges(self, dlrobot_human_file_info, dlrobot_db):
        sha256_to_human_file = dict()
        for domain in dlrobot_human_file_info:
            for sha256, file_info in dlrobot_human_file_info[domain].items():
                if 'filepath' in file_info:
                    sha256_to_human_file[sha256] = get_document_file_id(file_info)

        human_persons = self.get_mapping_section_to_stable_id()
        self._copy_human_merges(sha256_to_human_file, human_persons, dlrobot_db)

    def __init__(self, args):
        self.args = args
        self.declarator_db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                                        unix_socket="/var/run/mysqld/mysqld.sock")

        self.file_2_document = dict()
        self.document_2_files = defaultdict(set)
        self.office_names = dict()

        self.init_offices()
        self.init_file_2_documents()

    def __del__(self):
        self.declarator_db_connection.close()

    def get_human_smart_parser_json(self, failed_files):
        documents = set()
        for file_id in failed_files:
            document_id = self.file_2_document.get(file_id)
            if document_id is None:
                print("cannot find file {}".format(file_id))
            else:
                documents.add(document_id)

        for document_id in documents:
            all_doc_files = self.document_2_files[document_id]
            if len(all_doc_files & failed_files) == len(all_doc_files):
                filename = os.path.join(self.args.smart_parser_human_json, str(document_id) + ".json")
                if os.path.exists(filename):
                    print("import human file {}".format(filename))
                    yield filename, None, document_id


def import_one_smart_parser_json(dlrobot_db, office_name, filepath, source_file_sha256, document_id):
    with open(filepath, "r", encoding="utf8") as inp:
        input_json = json.load(inp)
    income_year = input_json.get('document', dict()).get('year')
    if income_year is None:
        print ("cannot import {}, year is not defined".format(filepath))
        return
    section_count = 0
    out_cursor = dlrobot_db.get_new_output_cursor()
    for p in input_json['persons']:
        person_info = p.get('person')
        if person_info is None:
            continue
        fio = person_info.get('name',  person_info.get('name_raw'))
        if fio is None:
            continue
        fio = normalize_whitespace(fio.replace('"', ' '))

        declarant_income = get_declarant_income(p)

        section_count += 1
        dlrobot_db.import_one_section( out_cursor,
                          fio,
                          int(income_year),
                          declarant_income,
                          p,
                          office_name,
                          source_file_sha256,
                          document_id)

    dlrobot_db.close_output_cursor_and_commit(out_cursor)
    print("import {} sections from {}".format(section_count, filepath))


def import_all_jsons(dlrobot_human_file_info, declarator_db, dlrobot_db):
    offices_to_domains = build_office_domains(dlrobot_human_file_info)

    for office_id, office_domains in offices_to_domains.items():
        for domain in office_domains:
            print ("office {} domain {}".format(office_id, domain))
            jsons_to_import = list()

            failed_files = set()
            for source_file_sha256, file_info in dlrobot_human_file_info[domain].items():
                input_path = os.path.join("domains", domain, file_info['dlrobot_path'])
                smart_parser_results = list(get_smart_parser_results(input_path))
                if len(smart_parser_results) == 0:
                    if 'filepath' in file_info:
                        failed_files.add(get_document_file_id (file_info))
                else:
                    for file_path in smart_parser_results:
                        jsons_to_import.append( (file_path, source_file_sha256, None) )

            jsons_to_import += list(declarator_db.get_human_smart_parser_json(failed_files))

            for file_path, source_file_sha256, document_id in jsons_to_import:
                try:
                    office_name = declarator_db.office_names[office_id]
                    import_one_smart_parser_json(dlrobot_db, office_name, file_path, source_file_sha256, document_id)
                except Exception as exp:
                    print("Error! cannot import {}: {} ".format(file_path, exp))
        #break