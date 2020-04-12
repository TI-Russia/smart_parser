from . import models
import sys
from declarations.management.commands.common import normalize_whitespace
from declarations.countries import get_country_code
import traceback
from django.db import DatabaseError


def read_incomes(section_json):
    for i in section_json.get('incomes', []):
        size = i.get('size')
        if isinstance(size, float) or (isinstance(size, str) and size.isdigit()):
            size = int(size)
        yield models.Income(size=size,
                     relative=models.Relative.get_relative_code(i.get('relative'))
                     )


def read_real_estates(section_json):
    for i in section_json.get('real_estates', []):
        own_type_str = i.get("own_type", i.get("own_type_by_column"))
        country_str = i.get("country", i.get("country_raw"))
        yield models.RealEstate(
            type=i.get("type", i.get("text")),
            country=get_country_code(country_str),
            relative=models.Relative.get_relative_code(i.get('relative')),
            owntype=models.OwnType.get_own_type_code(own_type_str),
            square=i.get("square"),
            share=i.get("share_amount")
        )


def read_vehicles(section_json):
    for i in section_json.get('vehicles', []):
        text = i.get("text")
        if text is not None:
            yield models.Vehicle(
                name=text,
                name_ru=text,
                relative=models.Relative.get_relative_code( i.get('relative'))
            )

def convert_to_int_with_nones(v):
    if v is None:
        return 0
    return int(v)

class TSmartParserJsonReader:

    class SerializerException(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return (repr(self.value))

    def __init__(self, income_year, spjsonfile, section_json):
        self.section_json = section_json
        self.section = models.Section(
            spjsonfile=spjsonfile,
            income_year=income_year,
        )
        self.init_person_info()
        self.incomes = list(read_incomes(section_json))
        self.real_estates = list(read_real_estates(section_json))
        self.vehicles = list(read_vehicles(section_json))

    def init_person_info(self):
        person_info = self.section_json.get('person')
        if person_info is None:
            raise TSmartParserJsonReader.SerializerException("cannot find 'person'  key in json")
        fio = person_info.get('name', person_info.get('name_raw'))
        if fio is None:
            raise TSmartParserJsonReader.SerializerException("cannot find 'name' or 'name_raw'in json")
        self.section.person_name =  normalize_whitespace(fio.replace('"', ' '))
        self.section.person_name_ru = self.section.person_name
        self.section.position =  person_info.get("role")
        self.section.position_ru = self.section.position
        self.section.department =  person_info.get("department")
        self.section.department_ru = self.section.department

    def set_section(self, related_records):
        for r in related_records:
            r.section = self.section
            yield r

    def get_section_passport(self):
        return "\t".join([
            str(self.section.spjsonfile.office.id),
            str(self.section.income_year),
            self.section.person_name,
            str(sum(convert_to_int_with_nones(i.size) for i in self.incomes)),
            str(sum(convert_to_int_with_nones(r.square) for r in self.real_estates)),
            str(sum(1 for v in self.vehicles))
        ])

    def save_to_database(self):
        self.section.save() # to obtain id
        models.Income.objects.bulk_create(self.set_section(self.incomes))
        models.RealEstate.objects.bulk_create(self.set_section(self.real_estates))
        models.Vehicle.objects.bulk_create(self.set_section(self.vehicles))
