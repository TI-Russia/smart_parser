

class TOfficeRubrics:
    Court = 1
    Municipality = 2
    Education = 3
    Military = 4
    Siloviki = 5
    Medicine = 6
    Prosecutor = 7
    Election = 8
    Legislature = 9
    Gulag = 10
    Tax = 11
    ExecutivePower = 19
    Other = 20



RubricsInRussian = {
    TOfficeRubrics.Court: {
        "name": "Суды",
        "keywords": ["судья", "арбитраж", " суда", " суды", " суд "],
        "top_parent": 626

    },
    TOfficeRubrics.Municipality: {
        "name": "Муниципалитеты",
        "keywords": ["сельсовет", "сельское поселение"],
        "top_parent": 627
    },
    TOfficeRubrics.Education: {
        "name": "Образование",
        "keywords": ["образования и науки"],
        "top_parent": 870
    },
    TOfficeRubrics.Military: {
        "name": "Военные",
        "keywords": ["министерство обороны"]
    },
    TOfficeRubrics.Siloviki: {
        "name": "Cиловики",
        "keywords": ["министерство внутренних дел", "мвд", "фмс", "фсб", "фсо", "росгвардия",
                     "миграцио", "безопасности", "федеральная служба охраны", "гвардии",
                     "cлужба внешней разведки"],
        "top_parent": 959

    },
    TOfficeRubrics.Medicine: {
        "name": "Здравоохранение",
        "keywords": ["здравоохранения", "больница"]
    },
    TOfficeRubrics.Prosecutor: {
        "name": "Прокуратура",
        "keywords": ["прокуратур"]
    },
    TOfficeRubrics.Legislature: {
        "name": "Законодательная власть",
        "keywords": ["законодатель", "депутат", "совет ", "совета", "дума", "собрани", "хурал", "парламент", ],
        "antikeywords": ["сельсовет"]
    },
    TOfficeRubrics.Election: {
        "name": "Избиркомы",
        "keywords": ["избиратель", "тик "]
    },
    TOfficeRubrics.Gulag: {
        "name": "ФСИН",
        "keywords": ["фсин", "наказан", "колония", "изолятор"]
    },
    TOfficeRubrics.Tax: {
        "name": "Налоги",
        "keywords": ["федеральная налоговая"],
        "immediate_parent": 470
    },
    TOfficeRubrics.ExecutivePower: {
        "name": "Исполнительная власть",
        "keywords": ["исполнительной", "правительств", "минист", "администрац", "управ", "департамент", "чрезвычайн", "гражданской обороны"],
        "top_parent": 11
    },
    TOfficeRubrics.Other: {
        "name": "Остальные",
    }
}


class TOfficeProps:
    def __init__(self, name, top_parent=None, immediate_parent=None):
        self.name = " " + name.lower() + " "  # search for ' суд '
        self.top_parent = top_parent
        self.immediate_parent = immediate_parent

    def check_rubric(self, rubric):
        if self.top_parent is not None:
            if self.top_parent == RubricsInRussian[rubric].get('top_parent'):
                return True

        if self.immediate_parent is not None:
            if self.immediate_parent == RubricsInRussian[rubric].get('immediate_parent'):
                return True

        for keyword in RubricsInRussian[rubric].get('antikeywords', []):
            if self.name.find(keyword) != -1:
                return False

        for keyword in RubricsInRussian[rubric].get('keywords', []):
            if self.name.find(keyword) != -1:
                return True

        if rubric == TOfficeRubrics.ExecutivePower:
            if 'федеральная служба' in self.name and \
                    not self.check_rubric(TOfficeRubrics.Siloviki) and \
                    not self.check_rubric(TOfficeRubrics.Tax):
                return True

        return False


def get_all_rubric_ids():
    return RubricsInRussian.keys()


def fill_combo_box_with_rubrics():
    return [('', '')] + list ( (k, v['name']) for k, v in RubricsInRussian.items())


def get_russian_rubric_str(rubric_id):
    return RubricsInRussian[rubric_id]['name']

