# -*- coding: utf-8 -*-

import json
import dedupe
import pickle
import re


def intersection_weight(set1, set2):
    return sum(set1.intersection(set2))


def num_category(field_1, field_2):
    return field_1


def abs_diff(field_1, field_2):
    return abs(float(field_1) - float(field_2))


def num_diff(field_1, field_2):
    return field_1 - field_2


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

    #{'field': 'realestates_shared_size', 'type': 'Custom', 'comparator': intersection_weight},

]

deduper = dedupe.Dedupe(fields, num_cores=2)
