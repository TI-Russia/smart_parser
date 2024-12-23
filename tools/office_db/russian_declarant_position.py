import re

ROLE_FIRST_WORDS = [
    "администратор", "ведущий", "врио", "генеральный", "глава", "главный",
    "государственная", "государственный", "директор", "должность", "доцент",
    "заведующая", "заведующий", "зам", "заместитель", "инспектор", "исполняющий", "консультант",
    "контролер", "начальник", "первый", "полномочный", "помощник",
    "поректор", "председатель", "представитель", "проректор",
    "ректор", "референт", "руководитель", "руководители", "секретарь", "советник",
    "специалист", "специальный", "старший", "статс", "судья",
    "технический", "уполномоченный", "управляющий", "финансовый",
    "член", "экономист", "юрисконсульт"
]
ROLE_FIRST_WORDS_REGEXP = "|".join(("(^{})".format(x) for x in ROLE_FIRST_WORDS))


def is_public_servant_role(s):
    return re.search(ROLE_FIRST_WORDS_REGEXP, s, re.IGNORECASE)
