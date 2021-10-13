from common.logging_wrapper import setup_logging

import sys
import pymysql
import argparse


def get_sql_cursor(sql):
    db = pymysql.connect(db="disclosures_db", user="disclosures", password="disclosures")
    cursor = db.cursor()
    cursor.execute(sql)
    for items  in cursor:
        yield items
    cursor.close()
    db.close()
    return sql


def get_missed_count(db_prod, db_dev):
    query = """
                select count(*) 
                from {}.declarations_person 
                where id not in (
                    select id 
                    from {}.declarations_person
                ) 
             """.format(db_prod, db_dev)

    for cnt, in get_sql_cursor(query):
        return cnt


def get_missed_examples(db_prod, db_dev, limit):
    query = """
                select id 
                from {}.declarations_person 
                where id not in (
                    select id 
                    from {}.declarations_person
                ) 
                limit {}
             """.format(db_prod, db_dev, limit)

    for id, in get_sql_cursor(query):
        yield id


def get_prod_count(db_prod):
    query = """
                select count(*) 
                from {}.declarations_person 
             """.format(db_prod)
    for cnt, in get_sql_cursor(query):
        return cnt


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples-count", dest='examples_count', type=int, default=1000)
    parser.add_argument("--prod-db", dest='prod_db_name', default='disclosures_db')
    parser.add_argument("--dev-db", dest='dev_db_name', default='disclosures_db_dev')
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging(log_file_name="check_person_id_permanence.log")
    missed_prod_count = get_missed_count(args.prod_db_name, args.dev_db_name)
    all_prod_count = get_prod_count(args.prod_db_name)
    for person_id in get_missed_examples(args.prod_db_name, args.dev_db_name, args.examples_count):
        logger.debug("missed person example https://disclosures.ru/person/{}".format(person_id))
    logger.info("person count in {}: {}".format(args.prod_db_name, all_prod_count))
    logger.info("missed person count in {}: {}".format(args.dev_db_name, missed_prod_count))
    min_permanence_level = 0.95
    permanence = (all_prod_count - missed_prod_count) / (all_prod_count + 0.0000001)
    if permanence < min_permanence_level:
        logger.error("Warning! Low person_id permanence: {:.5f} < {}, check your db if you want to publish this db in internet.".format(
            permanence, min_permanence_level))
        sys.exit(1)


if __name__ == "__main__":
    main()
