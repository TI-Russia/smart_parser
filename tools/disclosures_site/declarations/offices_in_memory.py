import json
import os

class TOfficeInMemory:

    def __init__(self, office_id=None, name=None, parent_id=None, type_id=None, rubric_id=None, region_id=None):
        self.office_id = office_id
        self.name = name
        self.parent_id = parent_id
        self.type_id = type_id
        self.rubric_id = rubric_id
        self.region_id = region_id

    def from_json(self, js):
        self.office_id = int(js['id'])
        self.name = js['name']
        self.parent_id = js['parent_id']
        self.type_id = js['type_id']
        self.rubric_id = js.get('rubric_id')
        self.region_id = js['region_id']
        return self


class TOfficeTableInMemory:
    SELECTED_OFFICES_FOR_TESTS = None
    group_types = set([10, 12, 16, 17]) # these offices do not exist like all Moscow courts

    def go_to_the_top(self, office_id):
        cnt = 0
        while True:
            cnt += 1
            if cnt > 5:
                raise Exception("too deep structure, probably a cycle found ")
            if self.offices[office_id].parent_id is None:
                return office_id
            parent: TOfficeInMemory
            parent = self.offices[self.offices[office_id].parent_id]
            if self.use_office_types:
                if parent.type_id in TOfficeTableInMemory.group_types:
                    return office_id
            office_id = parent.office_id
        return office_id

    def get_top_parent_office_id(self, office_id):
        return self.transitive_top[int(office_id)]

    def get_immediate_parent_office_id(self, office_id):
        if office_id is None:
            return None
        return self.offices[int(office_id)].parent_id

    def __init__(self, use_office_types=True):
        self.use_office_types = use_office_types
        self.offices = dict()
        self.transitive_top = dict()

    def _init_transitive(self):
        for office_id in self.offices:
            self.transitive_top[office_id] = self.go_to_the_top(office_id)

    def get_office_id_to_ml_office_id(self):
        return list((i, o) for i, o in enumerate(self.offices))

    # echo  "select *  from declarations_office" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator data/offices.txt
    # echo  "select * from declarator.declarations_office  where id not in (select id from disclosures_db.declarations_office)" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator > offices.txt

    def read_from_local_file(self):
        # without rubrics
        filepath = os.path.join(os.path.dirname(__file__), "../data/offices.txt")
        with open(filepath) as inp:
            offices = json.load(inp)
            for o in offices:
                office_id = int(o['id'])
                if TOfficeTableInMemory.SELECTED_OFFICES_FOR_TESTS is not None:
                    if office_id not in TOfficeTableInMemory.SELECTED_OFFICES_FOR_TESTS:
                        continue
                self.offices[office_id] = TOfficeInMemory().from_json(o)
        if TOfficeTableInMemory.SELECTED_OFFICES_FOR_TESTS is None:
            self._init_transitive()

    def read_from_table(self, table):
        for o in table:
            self.offices[o.id] = TOfficeInMemory(
                 office_id=o.id,
                 name=o.name,
                 parent_id=o.parent_id,
                 type_id=o.type_id,
                 rubric_id=o.rubric_id,
                 region_id=o.region_id
            )
        self._init_transitive()
