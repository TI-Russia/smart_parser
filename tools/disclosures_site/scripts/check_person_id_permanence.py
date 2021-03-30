from common.logging_wrapper import setup_logging

import sys
import pymysql


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


def main():
    prod_db = sys.argv[1]
    dev_db = sys.argv[2]
    logger = setup_logging(log_file_name="check_person_id_permanence.log")
    missed_prod_count = get_missed_count(prod_db, dev_db)
    all_prod_count = get_prod_count(prod_db)
    for person_id in get_missed_examples(prod_db, dev_db, 100):
        logger.debug("missed person example https://disclosures.ru/person/{}".format(person_id))
    logger.info("person count in {}: {}".format(prod_db, all_prod_count))
    logger.info("missed person count in {}: {}".format(dev_db, missed_prod_count))
    min_permanence_level = 0.95
    permanence = (all_prod_count - missed_prod_count) / (all_prod_count + 0.0000001)
    if permanence < min_permanence_level:
        logger.error("Warning! Low person_id permanence: {:.5f} < {}, check your db if you want to publish this db in internet.".format(
            permanence, min_permanence_level))
        sys.exit(1)


if __name__ == "__main__":
    main()
