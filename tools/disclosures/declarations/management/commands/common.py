import re


def normalize_whitespace(str):
    str = re.sub(r'\s+', ' ', str)
    str = str.strip()
    return str


def resolve_fullname(name, as_list=False):
    """
    Good fullnames (full list in test_serializers.py):
        resolve_fullname("Мамедов Чингиз Георгиевич")
        resolve_fullname("Мамедов ЧН")
        resolve_fullname("Мамедов ЧН.")
        resolve_fullname("МамедовЧН.")
        resolve_fullname("Мамедов Ч.Г.")
        resolve_fullname("Ч.Г. Мамедов")
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
    # clean up
    # Мурашев J1.JI.
    name = re.sub(r"J[1I].", u"Л.", name)
    name = re.sub(r"\s+\(м/с\)", u"", name, flags=re.U)
    parts = ()

    # proper full_name
    fio_re = re.compile(
        r"^([а-я\-А-ЯёЁ]+)\s+([а-яА-ЯёЁ]+\-?[а-яА-ЯёЁ]*)[.\s]+([а-яА-ЯёЁ]+\-?[а-яА-ЯёЁ]*)\.?(\s(\3))?(ЧФ)?(СФ)?$",
        flags=re.U)
    res = fio_re.match(name)

    if res:
        parts = res.groups()

    if not parts:
        # full name like "Мамедов Ч.Г.-О."
        fio_re = re.compile(
            r"^([а-я\-А-ЯёЁ]+)\s+([а-яА-ЯёЁ])[.\s]+([а-яА-ЯёЁ]+)[\.\-]+([а-яА-ЯёЁ]+)\.?$",
            flags=re.U)
        res = fio_re.match(name)
        if res:
            parts = res.groups()
            parts = parts[:2] + ("%s-%s" % (parts[2], parts[3]), )

    if not parts:
        # full name with minor bugs
        fio_re = re.compile(
            r"^([а-я\-А-ЯёЁ]+)\.?\s?([А-ЯЁ])\s?[.,]?\s?([А-ЯЁ])\s?[.,]?\.?$",
            flags=re.U)
        res = fio_re.match(name)
        if res:
            parts = res.groups()

    if not parts:
        # full name, but other order - "Ч.Г. Мамедов"
        fio_re = re.compile(
            r"^([А-ЯЁ])\s?[.,]?\s?([А-ЯЁ])\s?[.,]?\.?\s*([а-я\-А-ЯёЁ]+)\.?\s?$",
            flags=re.U)
        res = fio_re.match(name)
        if res:
            g = res.groups()
            parts = (g[2], g[0], g[1])

    if not parts:
        return None

    if as_list:
        return parts[:3]
    else:
        return {
            'family_name': parts[0],
            'name': parts[1],
            'patronymic': parts[2],
        }
