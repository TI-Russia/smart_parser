import re


def normalize_whitespace(str):
    str = re.sub(r'\s+', ' ', str)
    str = str.strip()
    return str

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
        items = list(re.split("[ .]+", person_name))
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

    def __eq__(self, other):
        return self.family_name == other.family_name and self.first_name == other.first_name \
               and self.patronymic == other.patronymic
