from collections import defaultdict
import re

SOME_OTHER_DOCUMENTS = [
    'шаблоны',
    'решение',
    'постановление',
    'доклад',
    'протокол',
    'план',
    'бланки',
    'утверждена',  # декларации не утверждают
    'реестр',
    'указ',
    'рейтинг',
    'распоряжение',
    'российская федерация федеральный закон',
    'приказ',
    'методические рекомендации',
    'график'
]


class TCharCategory:
    RUSSIAN = "ёйцукенгшщзхъфывапролджэячсмитьбю"
    LATIN = "qwertyuiopasdfghjklzxcvbnm"
    PUNCT = """'`@#$%^&*()_+`_+{}[]\|;:'"<>/?.,"""
    DIGIT = "1234567890"
    _chardict = dict()

    @staticmethod
    def initialize():
        TCharCategory._chardict = dict()
        for x in TCharCategory.RUSSIAN:
            TCharCategory._chardict[x] = 'RUSSIAN_CHAR'
        for x in TCharCategory.LATIN:
            TCharCategory._chardict[x] = 'LATIN_CHAR'
        for x in TCharCategory.PUNCT:
            TCharCategory._chardict[x] = 'PUNCT_CHAR'
        for x in TCharCategory.DIGIT:
            TCharCategory._chardict[x] = 'DIGIT_CHAR'

    @staticmethod
    def classify(text):
        res = defaultdict(int)
        for x in text:
            res[TCharCategory._chardict.get(x.lower(), 'OTHER_CHAR')] += 1
        return res

    @staticmethod
    def get_most_popular_char_category(text):
        res = list((v, k) for k, v in TCharCategory.classify(text).items())
        if len(res) == 0:
            return 'OTHER_CHAR'
        res.sort(reverse=True)
        return res[0][1]

TCharCategory.initialize()

def build_vehicle_regexp():
    vehicles = [
        "Opel", "Ситроен", "Subaru", "Мазда", "Mazda", "Peugeot", "Peageut", "BMW", "БМВ", "Ford", "Toyota", "Тойота",
        "KIA", "ТАГАЗ", "Шевроле", "Chevrolet", "Suzuki", "Сузуки", "Mercedes", "Мерседес", "Renault",
        "Мицубиси", "Rover", "Nissan", "Audi", "Вольво"
    ]

    #short and Russian
    ambiguous_vehicles = [
        "Опель", "Пежо", "Форд", "Рено", "Ровер", "Нисан", "Ауди"
    ]
    vehicle_items = list("({})".format(x) for x in vehicles) + list("(\\b{}\\b)".format(x) for x in ambiguous_vehicles)
    return "|".join(vehicle_items)

VEHICLE_REGEXP_STR = build_vehicle_regexp()


def russify(s):
    s = s.replace('O', 'О').replace('Х', 'Х').replace('E', 'Е').replace('C', 'С').replace('T', 'Т').replace('P', 'Р')
    s = s.replace('A', 'А').replace('H', 'Н').replace('K', 'К').replace('B', 'В').replace('M', 'М')
    s = s.replace('o', 'о').replace('x', 'х').replace('e', 'е').replace('c', 'с').replace('p', 'р').replace('a', 'а')
    s = s.replace('k', 'к')
    return s


def get_russian_normal_text_ratio(text):
    russian_stop_words = {
        'а', 'в', 'все', 'для', 'до', 'его', 'если', 'еще', 'же', 'за', 'и', 'из', 'или', 'иных', 'их', 'к', 'как',
        'который', 'которых', 'мы', 'на', 'не', 'о', 'об', 'он', 'от', 'по', 'при', 'при', 'с', 'свой', 'собой',
        'также', 'то', 'ты', 'у', 'этот', 'я'}
    words_count = 0.0
    stop_words_count = 0.0
    # no lower, remember initials
    for word in re.split('[^\w]+', text):
        if word in russian_stop_words:
            stop_words_count += 1
        words_count += 1
    return stop_words_count / (words_count + 0.00000001)


