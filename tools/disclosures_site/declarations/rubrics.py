import declarations.models as models

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
    ChiefExecutive = 19
    Other = 20


RubricsInRussian = {
    TOfficeRubrics.Court: {
        "name": "Суды",
        "keywords": ["судья", "арбитраж", " суда", " суды", " суд "],
        "top_parent": 626

    },
    TOfficeRubrics.Municipality: {
        "name": "Муниципалитеты",
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
        "name": "МВД, ФСБ и другие силовики",
        "keywords": ["министерство внутренних дел", "мвд", "фмс", "фсб", "фсо", "росгвардия",
                     "миграцио", "безопасности"],
        "top_parent": 959

    },
    TOfficeRubrics.Medicine: {
        "name": "Медицина",
        "keywords": ["здравоохранения", "больница"]
    },
    TOfficeRubrics.Prosecutor: {
        "name": "Прокуратура",
        "keywords": ["прокуратур"]
    },
    TOfficeRubrics.Legislature: {
        "name": "Законодательная власть",
        "keywords": ["законодатель", "депутат", "совет ", "совета", "дума", "собрани", "хурал", "парламент", ]
    },
    TOfficeRubrics.Election: {
        "name": "Избирательные комиссии",
        "keywords": ["избиратель", "тик "]
    },
    TOfficeRubrics.Gulag: {
        "name": "ФСИН",
        "keywords": ["фсин", "наказан", "колония", "изолятор"]
    },
    TOfficeRubrics.ChiefExecutive: {
        "name": "Исполнительная власть",
        "keywords": ["исполнительной", "правительств", "минист", "администрац", "управ", "департамент"],
        "top_parent": 11
    },
    TOfficeRubrics.Other: {
        "name": "Остальные",
    }
}


def get_russian_name(rubric_id):
    return RubricsInRussian[rubric_id]['name']


def check_rubric(office_hierarchy, office_id, rubric):
    top_parent = RubricsInRussian[rubric].get('top_parent')
    if top_parent is not None:
        if office_hierarchy.get_parent_office(office_id) == top_parent:
            return True

    keywords = RubricsInRussian[rubric].get('keywords')
    if keywords is not None:
        name = office_hierarchy.offices[office_id]['name'].lower()
        for keyword in keywords:
            if name.find(keyword) != -1:
                return True
    return False


def get_all_rubrics(office_hierarchy, office_id):
    return set(rubric for rubric in RubricsInRussian.keys() if check_rubric(office_hierarchy, office_id, rubric))


def build_one_rubric(logger, office_hierarchy, office_id):
    rubrics = get_all_rubrics(office_hierarchy, office_id)
    parent_id = office_hierarchy.offices[office_id]['parent_id']
    if len(rubrics) == 0 and parent_id is not None:
        rubrics = get_all_rubrics(office_hierarchy, parent_id)

    office_name = office_hierarchy.offices[office_id]['name']
    if len(rubrics) > 1 and TOfficeRubrics.ChiefExecutive in rubrics:
        rubrics.remove(TOfficeRubrics.ChiefExecutive)
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


def build_rubrics(logger=None):
    office_hierarchy = models.TOfficeHierarchy(use_office_types=False)
    for office in models.Office.objects.all():
        print("{} ".format(office.id))
        rubric_id = build_one_rubric(logger, office_hierarchy, office.id)
        if rubric_id is not None:
            office.rubric_id = rubric_id
            office.save()

