import pymysql
import json
import argparse
from declarator_db import TDeclaratorDBSqueezes, import_all_jsons


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dlrobot-human", required=True, dest='dlrobot_human')
    parser.add_argument("--smart-parser-human-json-folder", required=True, dest='smart_parser_human_json')
    return parser.parse_args()


class TDlRobotDB:
    def __init__(self):
        self.db_connection = pymysql.connect(db="dlrobotdb", user="dlrobotdb", password="dlrobotdb",
                                                unix_socket="/var/run/mysqld/mysqld.sock")
        self.section_table_name = "dlrobot_sections"

    def __del__(self):
        self.db_connection.close()

    def create_section_tables(self):
        cursor = self.get_new_output_cursor()
        cursor.execute("drop table if exists {};".format(self.section_table_name))
        cursor.execute(""" 
                    create table {} 
                            (id int NOT NULL AUTO_INCREMENT, 
                            original_fio longtext NOT NULL, 
                            income_year int NOT NULL,
                            declarant_income int,
                            office_name  longtext,
                            smart_parser_json longtext,
                            source_file_sha256 char(64),
                            person_id int,
                            declarator_document_id_if_dlrobot_failed int,
                            PRIMARY KEY (id) )
                            ENGINE=InnoDB
                            ROW_FORMAT=COMPRESSED 
                            KEY_BLOCK_SIZE=8;
                            """.format(self.section_table_name))
        self.close_output_cursor_and_commit(cursor)

    def create_tables(self):
        self.create_section_tables()

    def get_new_output_cursor(self):
        return self.db_connection.cursor()

    def close_output_cursor_and_commit(self, cursor):
        self.db_connection.commit()
        cursor.close()


    def import_one_section(self, cursor, fio, income_year, declarant_income, section_json,  office_name, source_file_sha256, document_id):
        section_json_str = json.dumps(section_json, ensure_ascii=False)
        sql = """ 
                INSERT INTO `{}` 
                       (original_fio, 
                        income_year,
                        declarant_income, 
                        smart_parser_json,
                        office_name,
                        source_file_sha256,
                        declarator_document_id_if_dlrobot_failed)
                VALUES ("{}",
                         {},
                         {},
                         JSON_QUOTE('{}'),
                        "{}",
                        "{}",
                         {}) 
              """.format( self.section_table_name,
                          fio,
                          int(income_year),
                          ("null" if declarant_income is None else declarant_income),
                          section_json_str.replace("'", "\\'"),
                          office_name.replace('"', '\\"'),
                          ("null" if source_file_sha256 is None else source_file_sha256),
                          ("null" if document_id is None else document_id),
                          )
        #print (sql)
        cursor.execute(sql)

    def iterate_all_sections(self):
        in_cursor = self.db_connection.cursor()
        in_cursor.execute(
            """select
                    id, 
                    original_fio,
                    income_year, 
                    declarant_income, 
                    source_file_sha256, 
                    declarator_document_id_if_dlrobot_failed 
                from {}

            """.format(self.section_table_name))
        for section_id, fio, income_year, declarant_income, source_file_sha256, document_id in in_cursor:
            yield section_id, fio, income_year, declarant_income, source_file_sha256, document_id
        in_cursor.close()

    def update_person_id(self, cursor, id, person_id):
        cursor.execute("update {} set person_id = {} where id={}".format(self.section_table_name, person_id, id))


if __name__ == '__main__':
    args = parse_args()
    declarator_db = TDeclaratorDBSqueezes(args)
    dlrobot_db = TDlRobotDB()

    with open(args.dlrobot_human, "r", encoding="utf8") as inp:
        dlrobot_human_file_info = json.load(inp)

    dlrobot_db.create_tables()
    import_all_jsons(dlrobot_human_file_info, declarator_db, dlrobot_db)
    declarator_db.copy_human_section_merges(dlrobot_human_file_info, dlrobot_db)
    del declarator_db
    del dlrobot_db
