import pymysql
import json
import os
import re
import argparse
from collections import defaultdict

DECLARATOR_DB_CONNECTION = None
DLROBOT_DB_CONNECTION = None

def init_db_connections():
    global DLROBOT_DB_CONNECTION, DECLARATOR_DB_CONNECTION
    DECLARATOR_DB_CONNECTION = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                unix_socket="/var/run/mysqld/mysqld.sock")

    DLROBOT_DB_CONNECTION = pymysql.connect(db="dlrobotdb", user="dlrobotdb", password="dlrobotdb",
                             unix_socket="/var/run/mysqld/mysqld.sock")

def close_db_connections():
    global DLROBOT_DB_CONNECTION, DECLARATOR_DB_CONNECTION
    DLROBOT_DB_CONNECTION.close()
    DECLARATOR_DB_CONNECTION.close()


def normalize_whitespace(str):
	str = re.sub(r'\s+', ' ', str)
	str = str.strip()
	return str

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dlrobot-human", required=True, dest='dlrobot_human')
    parser.add_argument("--smart-parser-human-json-folder", required=True, dest='smart_parser_human_json')
    return parser.parse_args()



class TDeclaratorDBSqueezes:

    def __init__(self):
        self.file_2_document = dict()
        self.document_2_files = defaultdict(set)

        in_cursor = DECLARATOR_DB_CONNECTION.cursor()
        in_cursor.execute("select id, document_id from declarations_documentfile")
        self.file_2_document = dict(x for x in in_cursor)
        for file_id, document_id in self.file_2_document.items():
            self.document_2_files[document_id].add(file_id)

        in_cursor.execute("select id, name from declarations_office")
        self.office_names  = dict ( (id,name) for id, name in in_cursor)
        in_cursor.close()



def create_section_tables():
    global DLROBOT_DB_CONNECTION
    out_cursor = DLROBOT_DB_CONNECTION.cursor()
    table_name = "dlrobot_sections";
    out_cursor.execute("drop table if exists {};".format(table_name))
    out_cursor.execute(""" 
                create table {} 
                        (id int NOT NULL AUTO_INCREMENT, 
                        original_fio longtext NOT NULL, 
                        income_year int NOT NULL,
                        office_name  longtext,
                        smart_parser_json longtext,
                        PRIMARY KEY (id) )""".format(table_name))
    out_cursor.close()


def create_tables():
    create_section_tables()


def build_office_domains(dlrobot_human_file_info):
    offices_to_domains = defaultdict(list)
    for domain in dlrobot_human_file_info:
        offices = list(x['office_id'] for x in dlrobot_human_file_info[domain].values() if 'office_id' in x)
        if len(offices) == 0:
            raise Exception("no office found for domain {}".format(domain))
        most_freq_office = max(set(offices), key=offices.count)
        offices_to_domains[most_freq_office].append(domain)
    return offices_to_domains


def get_smart_parser_results(input_path):
    if not  os.path.exists(input_path):
        # todo: why ?
        print("Error! cannot find {}, though it is in dlrobot_human.json".format(input_path))
        return

    if os.path.exists(input_path + ".json"):
        yield input_path + ".json"
    else:
        index = 0
        while True:
            filename  = input_path + "_{}.json".format(index)
            if not os.path.exists(filename):
                break
            yield filename
            index += 1



def get_human_smart_parser_json(args, declarator_db, failed_files):
    documents = set()
    for file_id in failed_files:
        document_id = declarator_db.file_2_document.get(file_id)
        if document_id is None:
            print ("cannot find file {}".format(file_id))
        else:
            documents.add(document_id)

    for d in documents:
        all_doc_files = declarator_db.document_2_files[d]
        if len (all_doc_files & failed_files) == len(all_doc_files):
            filename = os.path.join(args.smart_parser_human_json, str(d) + ".json")
            if os.path.exists(filename):
                print ("import human file {}".format(filename))
                yield filename


def import_json(declarator_db,  office_id, filepath):
    global DLROBOT_DB_CONNECTION
    office_name = declarator_db.office_names[office_id]
    with open(filepath, "r", encoding="utf8") as inp:
        input_json = json.load(inp)
    income_year = input_json.get('document', dict()).get('year')
    out_cursor = DLROBOT_DB_CONNECTION.cursor()
    if income_year is None:
        print ("cannot import {}, year is not defined".format(filepath))
        return
    section_count = 0
    for p in input_json['persons']:
        person_info = p.get('person')
        if person_info is None:
            continue
        fio = person_info.get('name',  person_info.get('name_raw'))
        if fio is None:
            continue
        fio = normalize_whitespace(fio.replace('"', ' '))
        section_count += 1
        person_json = json.dumps(p, ensure_ascii=False)
        sql = """ 
                INSERT INTO `dlrobot_sections` 
                       (original_fio, 
                        income_year, 
                        smart_parser_json,
                        office_name)
                VALUES ("{}",
                         {},
                        JSON_QUOTE('{}'),
                        "{}") 
              """.format( fio,
                          int(income_year),
                          person_json.replace("'", "\\'"),
                          office_name.replace('"', '\\"'))
        #print (sql)
        out_cursor.execute(sql)

    DLROBOT_DB_CONNECTION.commit()
    print("import {} sections from {}".format(section_count, filepath))


def main(args):
    create_tables()
    with open(args.dlrobot_human, "r", encoding="utf8") as inp:
        dlrobot_human_file_info = json.load(inp)
    offices_to_domains = build_office_domains(dlrobot_human_file_info)
    declarator_db = TDeclaratorDBSqueezes()
    for office_id, office_domains in offices_to_domains.items():

        for domain in office_domains:
            print ("office {} domain {}".format(office_id, domain))
            jsons_to_import = list()

            failed_files = set()
            for file_info in dlrobot_human_file_info[domain].values():
                input_path = os.path.join("domains", domain, file_info['dlrobot_path'])
                smart_parser_results = list(get_smart_parser_results(input_path))
                if len(smart_parser_results) == 0:
                    if 'filepath' in file_info:
                        file_id = os.path.splitext(os.path.basename(file_info['filepath']))[0]
                        if file_id.find('_') != -1:
                            file_id = file_id[0:file_id.find('_')]
                        failed_files.add(int(file_id))
                else:
                    jsons_to_import += smart_parser_results

            jsons_to_import += list(get_human_smart_parser_json(args, declarator_db, failed_files))

            for filepath in jsons_to_import:
                try:
                    import_json(declarator_db, office_id, filepath)
                except Exception as exp:
                    print("Error! cannot import {}: {} ".format(filepath, exp))



if __name__ == '__main__':
    args = parse_args()
    init_db_connections()
    main(args)
    close_db_connections()