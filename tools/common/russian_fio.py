import re
from common.primitives import normalize_whitespace

"""
Good fullnames (full list in test_serializers.py):
    resolve_fullname("Мамедов Чингиз Георгиевич")
    resolve_fullname("Мамедов ЧН")
    resolve_fullname("Мамедов ЧН.")
    resolve_fullname("МамедовЧН.")
    resolve_fullname("Мамедов Ч.Г.")
    resolve_fullname("Ч.Г. Мамедов")`
    resolve_fullname("Мамедов Ч.Г.-О.")
    resolve_fullname("Мамедов Ч.Г.О")
    resolve_fullname("Халиуллина Гульнур Ахметнагимовна Ахметнагимовна")
Bad fullnames (None):
    resolve_fullname("Мамедов Ч.")
    resolve_fullname("Иванов")
    resolve_fullname("квартира")
    resolve_fullname("Иванов ..")
    resolve_fullname("Мамедов ААА")
"""


class TRussianFio:
    def __init__(self, person_name, from_search_request=False):
        self.first_name = ""
        self.patronymic = ""
        self.family_name = ""
        if from_search_request:
            self.is_resolved = self.resolve_person_name_pattern_from_search_request(person_name)
        else:
            self.is_resolved = self.resolve_fullname(person_name)

    def build_from_parts(self, family_name, first_name, patronymic):
        self.family_name = family_name.lower()
        self.first_name = first_name.lower()
        self.patronymic = patronymic.lower()
        self.is_resolved = True
        return self

    def resolve_fullname(self, person_name):
        # clean up
        # Мурашев J1.JI.
        person_name = person_name.strip()
        person_name = re.sub(r"J[1I].", "Л.", person_name)
        person_name = re.sub(r"\s+\(м/с\)", "", person_name, flags=re.U)
        person_name = re.sub(r"\W+$", "", person_name)
        if re.match(r"^((жена)|(сын)|(дочь)|(супруг)|(супруга))\s+",  person_name, flags=re.IGNORECASE) is not None:
            return False
        if re.search(r"\s((жена)|(сын)|(дочь)|(супруг)|(супруга))$",  person_name, flags=re.IGNORECASE) is not None:
            return False
        parts = ()

        # proper full_name
        fio_re = re.compile(
            r"^([а-я\-А-ЯёЁ]+)\s+([а-яА-ЯёЁ]+\-?[а-яА-ЯёЁ]*)[.\s]+([а-яА-ЯёЁ]+\-?[а-яА-ЯёЁ]*)\.?(\s(\3))?(ЧФ)?(СФ)?$",
            flags=re.U)
        res = fio_re.match(person_name.replace(".", ""))

        if res:
            parts = res.groups()

        if not parts:
            # full name like "Мамедов Ч.Г.-О."
            fio_re = re.compile(
                r"^([а-я\-А-ЯёЁ]+)\s+([а-яА-ЯёЁ])[.\s]+([а-яА-ЯёЁ]+)[\.\-]+([а-яА-ЯёЁ]+)\.?$",
                flags=re.U)
            res = fio_re.match(person_name)
            if res:
                parts = res.groups()
                parts = parts[:2] + ("%s-%s" % (parts[2], parts[3]), )

        if not parts:
            # full name with minor bugs
            fio_re = re.compile(
                r"^([а-я\-А-ЯёЁ]+)\.?\s?([А-ЯЁ])\s?[.,]?\s?([А-ЯЁ])\s?[.,]?\.?$",
                flags=re.U)
            res = fio_re.match(person_name.replace(".", ""))
            if res:
                parts = res.groups()

        if not parts:
            # full name, but other order - "Ч.Г. Мамедов"
            fio_re = re.compile(
                r"^([А-ЯЁ])\s?[.,]?\s?([А-ЯЁ])\s?[.,]?\.?\s*([а-я\-А-ЯёЁ]+)\.?\s?$",
                flags=re.U)
            res = fio_re.match(person_name)
            if res:
                g = res.groups()
                parts = (g[2], g[0], g[1])

        if len(parts) > 0 and len(parts[0]) > 0:
            self.family_name = parts[0].lower()
            self.first_name = parts[1].lower()
            self.patronymic = parts[2].lower()
            return True
        return False

    def resolve_person_name_pattern_from_search_request(self, person_name):
        # Иванов
        # Иванов Иван
        # Иванов И.И.
        # Иванов Иван Иванович
        items = list(re.split("[ .]+", person_name.strip()))
        if len(items) > 0:
            self.family_name = items[0].lower()
        else:
            self.family_name = person_name.strip().lower()
            if len(self.family_name) == 0:
                return False
        if len(items) > 1:
            self.first_name = items[1].strip().lower()
        if len(items) > 2:
            self.patronymic = " ".join(items[2:]).strip().lower()
        return True

    # Жуков Иван Николаевич	Жуков И Н -> true
    # Жуков И Н	Жуков И Н -> true
    # Жуков И П	Жуков И Н -> false
    # Жуков Иван П	Жуков Исаак Н -> false

    def is_compatible_to(self, fio):
        return self.family_name == fio.family_name and \
                ((self.first_name.startswith(fio.first_name) and self.patronymic.startswith(fio.patronymic))
                 or (fio.first_name.startswith(self.first_name) and fio.patronymic.startswith(self.patronymic))
                )

    def __str__(self):
        return "{} {} {}".format(self.family_name, self.first_name, self.patronymic)

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other):
        return str(self) == str(other)

    def build_fio_with_initials(self):
        return "{} {} {}".format(self.family_name, self.first_name[0:1], self.patronymic[0:1])


POPULAR_RUSSIAN_NAMES = [
    "елена", "татьяна", "наталья", "ольга", "ирина", "светлана", "александр", "сергей", "марина",    "владимир", "людмила",
    "юлия", "галина", "алексей", "андрей", "анна", "екатерина", "надежда", "дмитрий", "оксана",    "николай", "валентина",
    "евгений", "лариса", "любовь", "юрий", "мария", "игорь", "михаил", "виктор", "анастасия",    "олег", "нина", "наталия",
    "вера", "евгения", "виктория", "валерий", "иван", "анатолий", "павел", "роман", "максим",    "вячеслав", "василий", "виталий",
    "денис", "инна", "константин", "александра", "тамара", "алла", "лилия", "олеся", "лидия",    "геннадий", "ксения", "дарья",
    "алена", "вадим", "маргарита", "антон", "жанна", "яна", "кристина", "петр", "артем",    "эльвира", "владислав", "илья",
    "альбина", "антонина", "станислав", "борис", "алина", "эдуард", "леонид", "раиса", "зоя", "вероника", "валерия", "зинаида",
    "артур", "диана", "елизавета", "кирилл", "алевтина", "григорий", "полина", "валентин",
    "римма", "георгий", "альберт", "анжела", "альфия", "федор", "дина", "никита", "эльмира", "алёна", "роза", "венера",
    "ульяна", "ангелина", "регина", "егор", "софья", "аркадий", "майя", "степан", "ярослав", "семен", "рита", "снежана",
    "артём", "клавдия", "варвара", "лев", "виолетта", "алиса", "даниил", "тимофей", "герман", "яков", "софия", "пётр",
    "евдокия", "фаина", "лена", "глеб", "родион", "ландыш", "юлиана", "марк", "фёдор", "тарас", "богдан", "рима", "иннокентий",
    "клара", "бэлла", "ростислав", "феликс", "вениамин", "нелля", "василина", "святослав", "руслана", "ян", "филипп", "матвей",
    "данила", "всеволод", "василиса", "афанасий", "захар", "гаврил", "ия", "семён", "артемий", "леся", "снежанна", "катерина",
    "ева", "виталия", "прасковья", "пелагея", "ярослава", "серафима", "владислава", "виталина", "октябрина", "прокопий",
    "матрена", "ефим", "арсений", "станислава", "мариана", "юлианна", "марфа", "леонтий", "эрнест", "игнат", "василь", "сталина",
    "крестина", "димитрий", "роксана", "капитолина", "кантемир", "парасковья", "олимпиада", "мальвина", "андриан", "акулина",
    "августа", "сирень", "лера", "степанида", "серафим", "августина", "анжелика", "карина", "руслан"
]

def is_title_case(s):
    return s.title() == s

class TRussianFioRecognizer:
    feminine_russian_patronymic_suffixes = {"вна", "чна"}
    masculine_russian_patronymic_suffixes = {"вич", "мич", "ьич", "тич"}
    russian_patronymic_suffixes = feminine_russian_patronymic_suffixes | masculine_russian_patronymic_suffixes

    @staticmethod
    def is_masculine_patronymic(s):
        return s.length() >= 5 and s[-3:].lower() in TRussianFioRecognizer.masculine_russian_patronymic_suffixes

    @staticmethod
    def is_feminine_patronymic(s):
        return s.length() >= 5 and s[-3:].lower() in TRussianFioRecognizer.feminine_russian_patronymic_suffixes

    @staticmethod
    def is_patronymic(s):
        return s.length() >= 5 and s.strip(',-').lower()[-3:] in TRussianFioRecognizer.russian_patronymic_suffixes

    @staticmethod
    def string_contains_Russian_name(name):
        if name.find('(') != -1:
            name = name[:name.find('(')].strip()
        words = name.split(' ')

        relatives = {"супруг", "супруга", "сын", "дочь"}
        while len(words) > 0 and words[-1].lower() in relatives:
            words = words[0:-1]

        if len(words) >= 0 and re.search('^[0-9]+[.]\s*$', words[0]) is not None:
            words = words[1:]

        if len(words) >= 3 and ( \
                TRussianFioRecognizer.is_russian_full_name(words[0],  words[1],  words[2]) or \
                TRussianFioRecognizer.is_russian_full_name(words[-3], words[-2], words[-1])):
            return True

        name = " ".join(words)
        if re.search('[А-Я]\s*[.]\s*[А-Я]\s*[.]\s*$', name) is not None:
            return True

        # Иванов И.И.
        if re.search('^[А-Я][а-я]+\s+[А-Я]\s*[.]\s*[А-Я]\s*[.]', name) is not None:
            return True

        # И.И. Иванов
        if re.search('[А-Я]\s*[.]\s*[А-Я]\s*[.][А-Я][а-я]+$', name) is not None:
            return True
        return False

    @staticmethod
    def prepare_for_search_index(str):
        if str is None:
            return None
        str = str.replace("Ё", "Е").replace("ё", "е")
        return str

    @staticmethod
    def is_russian_full_name(w1,w2,w3):
        #Иванов Иван Иванович
        return is_title_case(w1) and is_title_case(w2) and TRussianFioRecognizer.is_patronymic(w3)