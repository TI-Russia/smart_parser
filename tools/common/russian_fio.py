from common.primitives import normalize_whitespace
from common.russian_morph_dict import TRussianDictWrapper

import re
import os


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
    "августа", "сирень", "лера", "степанида", "серафим", "августина", "анжелика", "карина", "руслан", "мартин", 'флора',
    'инга', 'таймураз'
]

POPULAR_RUSSIAN_NAMES_SET = set(POPULAR_RUSSIAN_NAMES)


def is_title_case(s):
    return s.title() == s


def count_alpha(s):
    return sum(1 for i in s if i.isalpha())


class TRussianFio:
    fio_misspell_path = os.path.join(os.path.dirname(__file__), "../disclosures_site/data/misspell_bin")

    def __init__(self, person_name, from_search_request=False, make_lower=True):
        self.case = None
        self.input_person_name = person_name
        self.first_name = ""
        self.first_name_is_abridged = False
        self.patronymic = ""
        self.patronymic_is_abridged = False
        self.family_name = ""
        if from_search_request:
            self.is_resolved = self._resolve_person_name_pattern_from_search_request(person_name)
        else:
            self.is_resolved = self._resolve_fullname(person_name)
        if make_lower:
            self.first_name = self.first_name.lower()
            self.patronymic = self.patronymic.lower()
            self.family_name = self.family_name.lower()

    def build_from_parts(self, family_name, first_name, patronymic):
        self.family_name = family_name.lower()
        self.first_name = first_name.lower()
        self.patronymic = patronymic.lower()
        self.is_resolved = True
        return self

    def is_name_initial(self, s):
        return  (len(s) == 1 and s[0].isalpha() and s[0].upper() == s[0]) or \
                (len(s) == 2 and s[0].isalpha() and s[1] == '.') or \
                (len(s) == 3 and s[0] == '.' and s[1].isalpha() and s[2] == '.') or \
                (len(s) == 3 and s[0].isupper() and s[1] == '.' and s[2] == '.')

    @staticmethod
    def convert_to_rml_encoding(person_name):
        return person_name.replace(' ', '_').upper()

    @staticmethod
    def convert_from_rml_encoding(person_name):
        return " ".join(w.title() for w in person_name.split("_"))


    def set_first_name(self, s):
        if s.endswith('.'):
            self.first_name_is_abridged = True
        self.first_name = s.strip('.')

    def set_patronymic(self, s):
        if s.endswith('.'):
            self.patronymic_is_abridged = True
        self.patronymic = s.strip('.')

    @staticmethod
    def can_start_fio(w):
        return len(w) > 0 and w[0].isupper() and (
                TRussianDictWrapper.is_morph_surname_or_predicted(w) or TRussianDictWrapper.is_morph_first_name(w))

    @staticmethod
    def is_fio_in_text(words):
        if len(words) < 3:
            return False
        w1 = words[0].strip(", ")
        if len(w1) > 0 and w1[0].isupper():
            if TRussianFio.can_start_fio(w1):
                w2 = words[1].strip(", ")
                w3 = words[2].strip(", ")
                if TRussianFio(" ".join([w1, w2, w3])).is_resolved:
                    return True
        return False

    @staticmethod
    def delete_fios(words):
        i = 0
        while i < len(words):
            if i <= len(words) - 3:
                w1 = words[i]
                if len(w1) > 0 and w1[0].isupper():
                    if TRussianDictWrapper.is_morph_surname_or_predicted(w1) or TRussianDictWrapper.is_morph_first_name(w1):
                        w2 = words[i + 1]
                        w3 = words[i + 2]
                        if TRussianFio(" ".join([w1, w2, w3])).is_resolved:
                            i += 3
                            continue
            yield words[i]
            i += 1

    def get_normalized_person_name(self):
        if self.is_resolved:
            s = self.family_name.title() + " " + self.first_name.title()
            if self.first_name_is_abridged:
                s += '.'
            if len(self.patronymic) > 0:
                s += " " + self.patronymic.title()
                if self.patronymic_is_abridged:
                    s += '.'
            return s
        else:
            return normalize_whitespace(self.input_person_name).lower()

    def get_abridged_normalized_person_name(self):
        if not self.is_resolved:
            return normalize_whitespace(self.input_person_name).lower()
        s = self.family_name.title()
        if len(self.first_name) >= 1:
            s += " " + self.first_name[0].upper() + "."
        if len(self.patronymic) >= 1:
            s += " " + self.patronymic[0].upper() + "."
        return s


    def _check_name_initial_complex(self, s):
        if count_alpha(s) < 2:
            return False
        if s.count('.') > 1 and s.endswith('.'):
            #like Ч.Г.-О.
            self.set_first_name(s[:2])
            self.set_patronymic(s[2:])
        elif len(s) == 2 and s.upper() == s:
            #like ЧГ
            self.set_first_name(s[0] + ".")
            self.set_patronymic(s[1] + ".")
        elif len(s) == 3 and s.upper() == s and s[2] == '.':
            # like ЧГ.
            self.set_first_name(s[0] + ".")
            self.set_patronymic(s[1] + ".")
        elif len(s) == 3 and s.upper() == s and s[1] == '.':
            # like А.Е
            self.set_first_name(s[0] + ".")
            self.set_patronymic(s[2] + ".")
        elif len(s) == 3 and s[0].isupper() and s[1] == ',' and s[2].isupper():
            # like Морозова С,А
            self.set_first_name(s[0] + ".")
            self.set_patronymic(s[2] + ".")
        elif len(s) == 4 and s.upper() == s and s[1] == ',' and s[3] == '.':
            #Коротыч Д,С.
            self.set_first_name(s[0] + ".")
            self.set_patronymic(s[2] + ".")
        elif len(s) == 6 and s[1] == '.'  and s.lower().endswith('.о.'):
            #Зейналов Б.Н.о.
            self.set_first_name(s[0] + ".")
            self.set_patronymic(s[2:])
        elif len(s) == 5 and s[1] == '.' and s.lower().endswith('.о'):
            # Зейналов Б.Н.о
            self.set_first_name(s[0] + ".")
            self.set_patronymic(s[2:]+ ".")
        else:
            return False
        return True

    def _resolve_fullname(self, person_name):
        # clean up
        # Мурашев J1.JI.
        person_name = person_name.strip()
        person_name = re.sub(r"J[1I].", "Л.", person_name)
        person_name = re.sub(r"\s+\(м/с\)", "", person_name, flags=re.U)
        person_name = re.sub(r"[,;:\"'()\[\]%#{}@~`\\/?<>+=|*]+$", "", person_name) # not including full stop

        if re.match(r"^((жена)|(сын)|(дочь)|(супруг)|(супруга))\s+",  person_name, flags=re.IGNORECASE) is not None:
            return False
        if re.search(r"(\s|\()((жена)|(сын)|(дочь)|(супруг)|(супруга))$",  person_name, flags=re.IGNORECASE) is not None:
            return False
        person_name = re.sub("([\s.][А-ЯЁ])\s+[.]", "\\1.", person_name)
        person_name = person_name.replace('ѐ', 'ё').replace('ѐ', 'ё')
        lower_person = person_name.lower()

        patronymic2 = ""
        for patr2 in ['оглы', 'кызы', 'кзы', 'гызы']:
            if lower_person.endswith(patr2):
                patronymic2 = " " + person_name[-len(patr2):]
                person_name = person_name[:-len(patr2)].strip()

        #"МамедовЧГ.
        person_name = re.sub('([а-я])([А-Я])', r'\1 \2', person_name)
        count_full_stops = person_name.count('.')

        #Мамедов.Х.Н. but not Ф.И.О.
        if len(person_name) > 6 and person_name.count(' ') == 0 and person_name[-1] == '.' and person_name[-3] == '.' \
                and person_name[-5] == '.':
            person_name = person_name[:-5] + ' ' + person_name[-4:]


        if count_full_stops == 1 and person_name.endswith('.') and len(person_name)>1  and not person_name[-2].istitle():
            person_name = person_name[:-1].strip()
            count_full_stops = 0


        parts = list(w for w in person_name.split(' ') if len(w) > 0)

        if len(parts) == 4:
            #Изъюрова Вик- Тория Александровна
            p = parts[1].strip('-') + parts[2]
            if p.lower() in POPULAR_RUSSIAN_NAMES_SET:
                parts = [parts[0], p, parts[3]]

        if len(parts) == 2 and len(parts[0]) > 10 and TRussianFioRecognizer.has_patronymic_suffix(parts[1]):
            #Разогрееванина Николаевна
            for i in range(3, len(parts[0])-3):
                p1 = parts[0][:i]
                p2 = parts[0][i:]
                if TRussianFioRecognizer.has_surname_suffix(p1) or TRussianDictWrapper.is_morph_surname_not_predicted(p1):
                    if p2.lower() in POPULAR_RUSSIAN_NAMES_SET:
                        parts = [p1, p2.title(), parts[1]]
                        break

        if len(parts) == 4:
            #Пыжик Игорь Григорьев Ич
            p = parts[2] + parts[3].lower()
            if TRussianFioRecognizer.has_patronymic_suffix(p) and len(p) < 15 and len(parts[3]) <= 4:
                parts[2] = p
                parts = parts[:-1]

        if len(parts) == 4:
            #Великоречан Ина Е. Е.')
            p = parts[0] + parts[1].lower()
            if TRussianDictWrapper.is_in_dictionary(p):
                parts = [p, parts[2], parts[3]]

        if len(parts) == 3 and self._check_name_initial_complex(parts[2]):
            #Великоречан Ина Е.Е.')
            p = parts[0] + parts[1].lower()
            if TRussianDictWrapper.is_in_dictionary(p):
                parts = [p, parts[2]]

        count_Russian_words = 0
        if count_full_stops == 0:
            for i in parts:
                if not re.match('^[А-ЯЁ][а-яА-ЯЁё-]+$', i):
                    if not TRussianDictWrapper.is_morph_first_name(i) and \
                            not TRussianDictWrapper.is_morph_surname_not_predicted(i) and \
                            not TRussianFioRecognizer.has_patronymic_suffix(i):
                        break
                count_Russian_words += 1

        if len(parts) == 3 and self._check_name_initial_complex(parts[2]) and count_Russian_words == 2 and \
            not TRussianFioRecognizer.has_surname_suffix(parts[0]) and TRussianFioRecognizer.has_surname_suffix(parts[1]):
                parts[0] = [parts[0] + parts[1].lower(), parts[2]]

        max_word_weight = 0
        if count_Russian_words >= 3:
            word1_has_surname_suffix = TRussianFioRecognizer.has_surname_suffix(parts[0])
            word2_is_popular_name = parts[1].lower() in POPULAR_RUSSIAN_NAMES_SET
            word3_is_patronymic = TRussianFioRecognizer.has_patronymic_suffix(parts[2])
            weight = sum(1 for i in [word1_has_surname_suffix, word2_is_popular_name, word3_is_patronymic]  if i)
        else:
            weight = 0
        self.case = None
        if count_Russian_words == 3 and weight > 1:
            # Иванов Иван Иванович
            # Гулиев Гурбангули Арастун Оглы"
            self.family_name = parts[0]
            self.first_name = parts[1]
            self.patronymic = parts[2]
            self.case = "full_name_0"
        elif count_Russian_words > 3 and TRussianDictWrapper.is_morph_surname_not_predicted(parts[0]) and word3_is_patronymic:
            # or Russian name with garbage "Иванов Иван Иванович (председатель)"
            self.family_name = parts[0]
            self.first_name = parts[1]
            self.patronymic = parts[2].strip(',')
            self.case = "full_name_1"
        elif count_Russian_words == 3 and TRussianFioRecognizer.has_patronymic_suffix(parts[1]):
            #  Иван Иванович Иванов
            self.family_name = parts[2]
            self.first_name = parts[0]
            self.patronymic = parts[1]
            self.case = "full_name_2"
        elif count_Russian_words == 3 and TRussianDictWrapper.is_morph_surname_or_predicted(parts[0]):
            # not Russian name like "Заман Шамима Хасмат-Уз"
            self.family_name = parts[0]
            self.first_name = parts[1]
            self.patronymic = parts[2]
            self.case = "not_russian_names"
        elif count_Russian_words == 3 and weight == 1 and TRussianDictWrapper.get_max_word_weight(parts[0:3]) < 10:
            # Туба Давор Симович
            self.family_name = parts[0]
            self.first_name = parts[1]
            self.patronymic = parts[2]
            self.case = "full_name_rare"
        elif len(parts) == 3 and self.is_name_initial(parts[1]) and (self.is_name_initial(parts[2]) or self._check_name_initial_complex(parts[2])):
            # Иванов И. И.
            # Ахмедова З. М.-Т.
            self.family_name = parts[0]
            self.set_first_name(parts[1])
            self.set_patronymic(parts[2])
            self.case = "abbridged_name_1"
        elif len(parts) == 3 and self.is_name_initial(parts[0]) and self.is_name_initial(parts[1]):
            #  И. И. Иванов
            self.family_name = parts[2]
            self.set_first_name(parts[0])
            self.set_patronymic(parts[1])
            self.case = "abbridged_name_2"
        elif len(parts) == 3 and TRussianFioRecognizer.has_surname_suffix(parts[0]) and \
                TRussianDictWrapper.is_morph_first_name(parts[1]) \
                and self.is_name_initial(parts[2]):
            self.family_name = parts[0]
            self.set_first_name(parts[1])
            self.set_patronymic(parts[2])
            self.case = "patronymic_is_initial"
        elif len(parts) == 2 and self._check_name_initial_complex(parts[1]):
            # name like "Мамедов Ч.Г.-О."
            self.family_name = parts[0]
            self.case = "name_initial_complex1"
        elif len(parts) == 2 and self._check_name_initial_complex(parts[0]):
            #А.А. Кайгородова
            # name like "Ч.Г.-О. Мамедов "
            self.family_name = parts[1]
            self.case = "name_initial_complex2"
        elif len(parts) == 2 and TRussianFioRecognizer.has_surname_suffix(parts[0]) and \
              TRussianDictWrapper.is_morph_first_name(parts[1]):
            #Воецкая Ирина
            #Друзина Инна
            self.family_name = parts[0]
            self.first_name = parts[1]
            self.patronymic = ''
            self.case = "surname_and_name"

        elif len(parts) == 1 and count_full_stops == 2 and len(person_name) > 6 and \
                self._check_name_initial_complex(person_name[:4]):
            #А.В.Бойко
            self.family_name = person_name[4:]
            self.case = "name_initials_no_spaces"

        if self.case is None:
            return False

        if patronymic2 is not None:
            self.patronymic = self.patronymic + patronymic2

        return True

    def _resolve_person_name_pattern_from_search_request(self, person_name):
        # Иванов
        # Иванов Иван
        # Иванов И.И.
        # Иванов Иван Иванович
        items = list(re.split("[ .]+", person_name.strip()))
        if len(items) > 0:
            self.family_name = items[0]
        else:
            self.family_name = person_name.strip()
            if len(self.family_name) == 0:
                return False
        if len(items) > 1:
            self.first_name = items[1].strip()
        if len(items) > 2:
            self.patronymic = " ".join(items[2:]).strip()
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


class TRussianFioRecognizer:
    feminine_russian_patronymic_suffixes = {"вна", "чна"}
    masculine_russian_patronymic_suffixes = {"вич", "мич", "ьич", "тич"}
    russian_patronymic_suffixes = feminine_russian_patronymic_suffixes | masculine_russian_patronymic_suffixes
    russian_family_name_suffixes = {'ва', 'ов', 'на', 'ин', 'ев', 'ко', 'ая', 'ий', 'ик'}

    @staticmethod
    def is_masculine_patronymic(s):
        return len(s) >= 5 and s[-3:].lower() in TRussianFioRecognizer.masculine_russian_patronymic_suffixes

    @staticmethod
    def is_feminine_patronymic(s):
        return len(s) >= 5 and s[-3:].lower() in TRussianFioRecognizer.feminine_russian_patronymic_suffixes

    @staticmethod
    def has_patronymic_suffix(s):
        return len(s) >= 5 and s.strip(',-').lower()[-3:] in TRussianFioRecognizer.russian_patronymic_suffixes

    @staticmethod
    def has_surname_suffix(s):
        return len(s) >= 5 and s.strip(',-').lower()[-2:] in TRussianFioRecognizer.russian_family_name_suffixes

    @staticmethod
    def string_contains_Russian_name(rus_text):
        rus_text = rus_text.strip()
        if rus_text.find('(') != -1:
            rus_text = rus_text[:rus_text.find('(')].strip()
        words = rus_text.split(' ')

        relatives = {"супруг", "супруга", "сын", "дочь"}
        while len(words) > 0 and words[-1].lower() in relatives:
            words = words[0:-1]

        if len(words) > 0 and re.search('^[0-9]+[.]\s*$', words[0]) is not None:
            words = words[1:]

        if len(words) >= 3 and ( \
                TRussianFioRecognizer.is_russian_full_name(words[0],  words[1],  words[2]) or \
                TRussianFioRecognizer.is_russian_full_name(words[-3], words[-2], words[-1])):
            return True

        rus_text = " ".join(words)
        if re.search('[А-ЯЁ]\s*[.]\s*[А-ЯЁ]\s*[.]\s*$', rus_text) is not None:
            return True

        # Иванов И.И.
        if re.search('^[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\s*[.]\s*[А-ЯЁ]\s*[.]', rus_text) is not None:
            return True

        # И.И. Иванов
        if re.search('[А-ЯЁ]\s*[.]\s*[А-ЯЁ]\s*[.][А-ЯЁ][а-яё]+$', rus_text) is not None:
            return True
        return False

    @staticmethod
    def prepare_for_search_index(str):
        if str is None:
            return None
        str = str.replace("Ё", "Е").replace("ё", "е")
        return str

    @staticmethod
    def is_russian_full_name(w1, w2, w3):
        #Иванов Иван Иванович
        return is_title_case(w1) and is_title_case(w2) and TRussianFioRecognizer.has_patronymic_suffix(w3)