from django.db import models
from django.utils.translation import  get_language
from .countries import  get_country_str


def get_django_language():
    lang = get_language().lower()
    if len(lang) > 2:
        lang = lang[:2]
    return lang


class Office(models.Model):
    name = models.TextField(verbose_name='office name')


class Relative:
    main_declarant_code = "D"
    spouse_code = "S"
    child_code = "C"
    unknown_code = "?"
    code_to_info = dict()
    russian_to_code = dict()

    @staticmethod
    def get_relative_code(russian_name):
        if russian_name is None:
            return Relative.main_declarant_code
        r = russian_name.strip(" \n\r\t").lower()
        return Relative.russian_to_code.get(r, Relative.unknown_code)

    @staticmethod
    def static_initalize():
        Relative.code_to_info = {
            Relative.main_declarant_code:  {"ru": "", "en": "", "visual_order": 0},  # main public servant
            Relative.spouse_code: {"ru": "супруг(а)", "en": "spouse", "visual_order": 1},
            Relative.child_code: {"ru": "ребенок", "en": "child", "visual_order": 2},
            Relative.unknown_code: {"ru": "иное", "en": "other", "visual_order": 3},
        }
        Relative.russian_to_code = dict(((value['ru'], key) for key, value in Relative.code_to_info.items()))

    def __init__(self, code):
        self.code = code

    @property
    def name(self):
        info = Relative.code_to_info[self.code]
        return info.get(get_django_language(), info.get("en"))

    def __hash__(self):
        return ord(self.code)

    def __eq__(self, other):
        return self.code == other.code

    @staticmethod
    def sort_by_visual_order(items):
        if len(items) == 0:
            return items
        return sorted(items, key=(lambda x: Relative.code_to_info[x.code]['visual_order']))


Relative.static_initalize()


class OwnType:
    property_code = "P"
    code_to_info = dict()
    russian_to_code = dict()

    @staticmethod
    def get_own_type_code(russian_name):
        if russian_name is None:
            return OwnType.property_code
        r = russian_name.strip(" \n\r\t").lower()
        return OwnType.russian_to_code.get(r, OwnType.property_code)


    @staticmethod
    def static_initalize():
        OwnType.code_to_info = {
            OwnType.property_code: {"ru": "В собственности", "en": "private"},
            "U": {"ru": "В пользовании", "en": "in use"},
            "?": {"ru": "иное", "en": "other"},
        }
        OwnType.russian_to_code = dict((value['ru'], key) for key, value in OwnType.code_to_info.items())


OwnType.static_initalize()



class DocumentFile(models.Model):
    office = models.ForeignKey('declarations.Office', verbose_name="office name", on_delete=models.CASCADE)
    sha256 = models.CharField(max_length=200)
    web_domain = models.CharField(max_length=64)
    file_path = models.CharField(max_length=64)


class Person(models.Model):
    pass


class RealEstate(models.Model):
    section = models.ForeignKey('declarations.Section', on_delete=models.CASCADE)
    type = models.TextField(verbose_name='office name')
    country = models.CharField(max_length=2)
    relative = models.CharField(max_length=1)
    owntype = models.CharField(max_length=1)
    square = models.IntegerField(null=True)
    share = models.FloatField(null=True)

    @property
    def own_type_str(self):
        info = OwnType.code_to_info[self.owntype]
        return info.get(get_django_language(), info.get("en"))

    @property
    def country_str(self):
        return get_country_str(self.country, get_django_language())


class Vehicle(models.Model):
    section = models.ForeignKey('declarations.Section', on_delete=models.CASCADE)
    relative = models.CharField(max_length=1)
    name = models.TextField()


class Income(models.Model):
    section = models.ForeignKey('declarations.Section', on_delete=models.CASCADE)
    size = models.IntegerField(null=True)
    relative = models.CharField(max_length=1)


def get_relatives(records):
    return set( Relative(x.relative) for x in records.all())


class Section(models.Model):
    document_file = models.ForeignKey('declarations.DocumentFile', null=True, verbose_name="document file", on_delete=models.CASCADE)
    person = models.ForeignKey('declarations.Person', null=True, verbose_name="person id", on_delete=models.CASCADE)
    person_name = models.TextField(verbose_name='person name')
    income_year = models.IntegerField(null=True)
    department = models.TextField(null=True)
    position = models.TextField(null=True)

    @property
    def section_parts(self):
        relatives = set()
        relatives |= get_relatives(self.income_set)
        relatives |= get_relatives(self.realestate_set)
        relatives |= get_relatives(self.vehicle_set)
        result = Relative.sort_by_visual_order(list(relatives))
        return result

