import re


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
    TOfficeRubrics.ExecutivePower: {
        "name": "Исполнительная власть",
        "keywords": ["исполнительной", "правительств", "минист", "администрац", "управ", "департамент", "чрезвычайн", "гражданской обороны"],
        "top_parent": 11
    },
    TOfficeRubrics.Other: {
        "name": "Остальные",
    }
}

def get_all_rubric_ids():
    return RubricsInRussian.keys()


def fill_combo_box_with_rubrics():
    return [('', '')] + list ( (k, v['name']) for k, v in RubricsInRussian.items())


def get_russian_rubric_str(rubric_id):
    return RubricsInRussian[rubric_id]['name']


def check_rubric(office_name, parent_office_id, rubric):
    top_parent = RubricsInRussian[rubric].get('top_parent')
    if top_parent is not None:
        if parent_office_id == top_parent:
            return True

    name = " " + office_name.lower() + " "  # search for ' суд '

    for keyword in RubricsInRussian[rubric].get('antikeywords', []):
        if name.find(keyword) != -1:
            return False

    for keyword in RubricsInRussian[rubric].get('keywords', []):
        if name.find(keyword) != -1:
            return True


    if rubric == TOfficeRubrics.ExecutivePower:
        if 'федеральная служба' in office_name.lower() and not check_rubric(office_name, parent_office_id, TOfficeRubrics.Siloviki):
            return True

    return False


def get_all_rubrics(office_hierarchy, office_id):
    all_rubrics = set()
    for rubric in RubricsInRussian.keys():
        if check_rubric(office_hierarchy.offices[office_id]['name'],
                        office_hierarchy.get_parent_office_id(office_id),
                        rubric):
            all_rubrics.add(rubric)
    return all_rubrics


def build_office_rubric(logger, office_hierarchy, office_id):
    rubrics = get_all_rubrics(office_hierarchy, office_id)
    parent_id = office_hierarchy.offices[office_id]['parent_id']
    if len(rubrics) == 0 and parent_id is not None:
        rubrics = get_all_rubrics(office_hierarchy, parent_id)

    office_name = office_hierarchy.offices[office_id]['name']
    if len(rubrics) > 1 and TOfficeRubrics.ExecutivePower in rubrics:
        rubrics.remove(TOfficeRubrics.ExecutivePower)
    rubric = None
    if len(rubrics) == 0:
        if logger is not None:
            logger.error("cannot find rubric for {} set Other".format(office_name))
        rubric = TOfficeRubrics.Other
    elif len(rubrics) == 1:
        rubric = list(rubrics)[0]
        if logger is not None:
            logger.debug("{} => {}".format(office_name, RubricsInRussian[rubric]['name']))
    elif TOfficeRubrics.Education in rubrics:
        rubrics = {TOfficeRubrics.Education}
        rubric = list(rubrics)[0]
        if logger is not None:
            logger.debug("{} => {}".format(office_name, RubricsInRussian[rubric]['name']))
    else:
        rubric_strs = list(RubricsInRussian[r]['name'] for r in rubrics)
        if logger is not None:
            logger.error("ambiguous office {} rubrics:{} ".format(office_name, ",".join(rubric_strs)))
    return rubric


def convert_municipality_to_education(section_position):
    if section_position is None:
        return False
    heavy_position = re.search('(завуч|учитель|учительница)', section_position, re.IGNORECASE)  is not None
    light_position = re.search('(директор|заведующая|директора)', section_position, re.IGNORECASE) is not None
    edu_office = re.search('СОШ|СШ|МКОУ|МБУДО|МАОУ|ГБОУ|МОУ|колледж|ВСОШ|общеобразовательного|образовательным|школы|интерната', section_position) != None
    return heavy_position or (light_position and edu_office)