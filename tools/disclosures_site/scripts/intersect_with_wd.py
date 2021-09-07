from common.wiki_bots import send_sparql_request
import os
import json
from collections import defaultdict


def read_from_db():
    path =  "person.txt"
    if not os.path.exists(path):
        cmd = 'echo "select id, person_name from declarations_person" | mysql -D disclosures_db -u disclosures -pdisclosures > {}'.format(path)
        os.system(cmd)
    persons = defaultdict(list)
    with open (path) as inp:
        inp.readline()
        for line in inp:
            line = line.strip()
            if line.find("\t") != -1:
                person_id, person_name = line.split("\t")
                persons[person_name].append(int(person_id))
    return persons

def read_from_sparql():
    path = "sparql_data.txt"
    if not os.path.exists(path):
        sparql = """
        SELECT ?human ?humanLabel
        WHERE
        {
          ?human wdt:P31 wd:Q5 .       #find humans
          ?human wdt:P27 wd:Q159 .   #with at least one truthy P40 (child) statement defined to be "no value"
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],ru" }
        }
        limit 100        
        """
        data = send_sparql_request(sparql)
        with open(path, "w")  as outp:
            json.dump(data, outp)
    with open(path) as inp:
        return json.load(inp)


if __name__ == '__main__':
    wikidata = read_from_sparql()
    db_persons = read_from_db()
    for w in wikidata['results']['bindings']:
        name = w['humanLabel']['value']
        wikidata_url = w['human']['value']
        if name.find(',') != -1:
            name = name.replace(',', '')
        else:
            if len(name.split(" ")) == 3:
                w1,w2,w3 = name.split(" ")
                name = " ".join([w3, w1, w2])
        if name in db_persons:
            print("{} {} -?> {}".format(name, wikidata_url, db_persons[name]))
