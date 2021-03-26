import sys
import pymysql


def get_missed_count(db_prod, db_dev):
    db = pymysql.connect(db="disclosures_db", user="disclosures", password="disclosures")
    query = """
                select count(*) 
                from {}.declarations_person 
                where id not in (
                    select id 
                    from {}.declarations_person
                ) 
             """.format(db_prod, db_dev)
    cursor = db.cursor()
    cursor.execute(query)
    missed_count = None
    for cnt,  in cursor:
        missed_count = cnt
    cursor.close()

    query = """
                select count(*) 
                from {}.declarations_person 
             """.format(db_prod)
    cursor = db.cursor()
    cursor.execute(query)
    prod_count = None
    for cnt,  in cursor:
        prod_count = cnt
    cursor.close()

    db.close()
    return missed_count, prod_count


def main():
    prod_db = sys.argv[1]
    dev_db = sys.argv[2]
    missed_prod_count, all_prod_count = get_missed_count(prod_db, dev_db)
    print("person count in {}: {}".format(prod_db, all_prod_count))
    print("missed person count in {}: {}".format(dev_db, missed_prod_count))
    min_permanence_level = 0.95
    permanence = (all_prod_count - missed_prod_count) / (all_prod_count + 0.0000001)
    if permanence < min_permanence_level:
        print("Warning! Low person_id permanence: {:.5f} < {}, check your db if you want to publish this db in internet.".format(
            permanence, min_permanence_level))
        sys.exit(1)


if __name__ == "__main__":
    main()
