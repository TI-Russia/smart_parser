from collections import defaultdict

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
    'рейтинг'
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