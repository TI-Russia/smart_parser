# -*- coding: utf-8 -*-

import json
import dedupe
import pickle
import re


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


def list_intersection(list1, list2):
    set_list1 = set(d for d in list1)
    set_list2 = set(d for d in list2)
    return len(set_list1.intersection(set_list2))


def intersection_weight(set1, set2):
    return sum(set1.intersection(set2))

def num_category(field_1, field_2):
    return field_1

def abs_diff(field_1, field_2):
    return abs(float(field_1) - float(field_2))

def num_diff(field_1, field_2):
    return field_1 - field_2

def float_diff(field_1, field_2):
    return float(field_1) - float(field_2)

fields = [
    {'field': 'full_name', 'variable name': 'person', 'type': 'String'},

    {'field': 'family_name', 'variable name': 'person', 'type': 'String'},
    {'field': 'name_char', 'type': 'ShortString'},
    {'field': 'patronymic_char', 'type': 'ShortString'},

    {'field': 'person_income', 'variable name': 'person_income', 'type': 'Price', 'has missing': True},
    {'field': 'spource_income', 'type': 'Price', 'has missing': True},

    {'field': 'realestates', 'type': 'Set'},
    {'field': 'vehicles', 'type': 'Set'},

    {'field': 'offices', 'type': 'Set'},
    {'field': 'roles', 'type': 'Set'},

    {'field': 'surname_freq', 'type': 'Custom', 'comparator': num_category},
    {'field': 'children_real_estate', 'type': 'Custom', 'comparator': abs_diff},

    {'field': 'children_number', 'type': 'Custom', 'comparator': num_diff},
    {'field': 'min_year', 'type': 'Custom', 'comparator': num_diff},

    {'field': 'realestates_shared_size', 'type': 'Custom', 'comparator': intersection_weight},

]

deduper = dedupe.Dedupe(fields, num_cores=2)
