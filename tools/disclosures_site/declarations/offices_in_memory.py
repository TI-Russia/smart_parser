
class TOfficeInMemory:
    def __init__(self, office_id=None, name=None, parent_id=None, type_id=None, rubric_id=None, region_id=None):
        self.id = office_id
        self.name = name
        self.parent_id = parent_id
        self.type_id = type_id
        self.rubric_id = rubric_id
        self.region_id = region_id

    def from_json(self, js):
        self.id = js['id']
        self.name = js['name']
        self.parent_id = js['parent_id']
        self.type_id = js['type_id']
        self.rubric_id = js.get('rubric_id')
        self.region_id = js['region_id']
        return self


class TOfficeTableInMemory:
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
            office_id = parent.id
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

    def read_from_json(self, js):
        # without rubrics
        for o in js:
            self.offices[o['id']] = TOfficeInMemory().from_json(o)
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
