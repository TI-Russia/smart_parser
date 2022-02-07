from . import models
from common.primitives import normalize_whitespace
from office_db.countries import get_country_code
from office_db.rubrics import TOfficeRubrics
from declarations.section_passport import TSectionPassportItems1,TSectionPassportItems2
from office_db.offices_in_memory import TOfficeTableInMemory
from common.russian_fio import TRussianFio
from office_db.russia import RUSSIA
import re


def read_incomes(section_json):
    for i in section_json.get('incomes', []):
        size = i.get('size')
        if isinstance(size, float) or (isinstance(size, str) and size.isdigit()):
            size = int(size)

        yield models.Income(size=size,
                     relative=models.Relative.get_relative_code(i.get('relative')),
                     relative_index=i.get('relative_index')
                     )


def read_real_estates(section_json):
    for i in section_json.get('real_estates', []):
        own_type_str = None
        for key in [ "own_type",                # this line is to be deleted (it is not in JSON specification, I do know where it is used)
                     "own_type_by_column",  # from column heading  
                     "own_type_raw",   #some string f   rom an additional column or from the text
                     "owntype_raw"   #owntype_raw is a synonym of own_type_raw, that is used by declarator export json, better rename it in future
                   ]:
            own_type_str = i.get(key)
            if own_type_str is not None:
                break
        country_str = i.get("country", i.get("country_raw"))
        yield models.RealEstate(
            type=i.get("type", i.get("text", i.get('type_raw'))),
            country=get_country_code(country_str),
            relative=models.Relative.get_relative_code(i.get('relative')),
            owntype=models.OwnType.get_own_type_code(own_type_str),
            square=i.get("square"),
            share=i.get("share_amount"),
            relative_index=i.get('relative_index')
        )


def read_vehicles(section_json):
    for i in section_json.get('vehicles', []):
        text = i.get("text")
        if text is not None:
            yield models.Vehicle(
                name=text,
                relative=models.Relative.get_relative_code( i.get('relative')),
                relative_index=i.get('relative_index')
            )


def convert_to_int_with_nones(v):
    if v is None:
        return 0
    return int(v)


def normalize_fio_before_db_insert(fio):
    fio = normalize_whitespace(fio)
    fio = fio.replace('"', ' ').strip()
    fio = fio.strip('-')
    if len(fio) > 0 and fio[0].isdigit():
        while len(fio) > 0 and (fio[0].isdigit() or fio[0] == ' ' or fio[0] == '.'):
            fio = fio[1:]
    return fio.title()


class TSmartParserSectionJson:

    class SerializerException(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)

    def __init__(self, income_year, office_id, source_document):
        self.section = models.Section(
            source_document=source_document,
            income_year=income_year,
            office_id=office_id
        )
        self.incomes = None
        self.real_estates = None
        self.vehicles = None

    def init_rubric(self):
        # json_reader.section.rubric_id = source_document_in_db.office.rubric_id does not work
        # may be we should call source_document_in_db.refresh_from_db
        self.section.rubric_id = RUSSIA.get_office(self.section.office.id).rubric_id

        if self.section.rubric_id == TOfficeRubrics.Municipality and \
                TOfficeTableInMemory.convert_municipality_to_education(self.section.position):
            self.section.rubric_id = TOfficeRubrics.Education

    def read_raw_json(self, section_json):
        self.init_person_info(section_json)
        self.incomes = list(read_incomes(section_json))
        self.real_estates = list(read_real_estates(section_json))
        self.vehicles = list(read_vehicles(section_json))
        self.init_rubric()
        return self

    def get_main_declarant_income_size(self):
        for i in self.incomes:
            if i.relative == models.Relative.main_declarant_code:
                return i.size

    def init_person_info(self, section_json):
        person_info = section_json.get('person')
        if person_info is None:
            fio = section_json.get('fio')
            if fio is None:
                raise TSmartParserSectionJson.SerializerException("cannot find nor 'person' neither 'fio' key in json")
        else:
            fio = person_info.get('name', person_info.get('name_raw'))
            if fio is None:
                raise TSmartParserSectionJson.SerializerException("cannot find 'name' or 'name_raw'     in json")
        fio = normalize_fio_before_db_insert(fio)
        resolved_fio = TRussianFio(fio)
        if not resolved_fio.is_resolved:
            raise TSmartParserSectionJson.SerializerException("cannot resolve person name {}".format(fio))
        self.section.person_name = resolved_fio.get_normalized_person_name()
        self.section.position = person_info.get("role")
        self.section.department = person_info.get("department")

    def get_passport_components1(self):
        return TSectionPassportItems1(
                    self.section.office.id,
                    self.section.income_year,
                    self.section.person_name,
                    sum(convert_to_int_with_nones(i.size) for i in self.incomes),
                    sum(convert_to_int_with_nones(r.square) for r in self.real_estates),
                    sum(1 for v in self.vehicles)
                    )

    def get_passport_components2(self):
        return TSectionPassportItems2(
                    self.section.source_document.id,
                    self.section.income_year,
                    self.section.person_name,
                    sum(convert_to_int_with_nones(i.size) for i in self.incomes)
                    )

    def set_section(self, related_records):
        for r in related_records:
            r.section = self.section
            yield r

    def save_to_database(self, id):
        self.section.id = id
        self.section.save()
        models.Income.objects.bulk_create(self.set_section(self.incomes))
        models.RealEstate.objects.bulk_create(self.set_section(self.real_estates))
        models.Vehicle.objects.bulk_create(self.set_section(self.vehicles))


def whitespace_remover(val):
    """
    Return modified val where all consequent
    whitespaces replaced with space
    """
    return (re.sub('\s+', ' ', val)).strip()


def build_person_info_json(section):
    fio = section.person_name
    if fio is None or len(fio) == 0 and section.person is not None:
        fio = section.person.person_name

    person_info = {
        "name_raw": fio
    }
    if section.position:
        person_info['role'] = whitespace_remover(section.position)
    if section.department:
        person_info['department'] = whitespace_remover(section.department)
    return person_info


def get_relative_str(some_record):
    name = models.Relative(some_record.relative).name
    if len(name) == 0:
        return None
    else:
        return name


def get_section_json(section):
    """Returns Json section representation for yandex.toloka TSV """
    section_json = {"person": build_person_info_json(section)}

    section_json['incomes'] = []
    for income in section.income_set.all():
        section_json['incomes'].append ({"size": income.size, "relative": get_relative_str(income)})

    for v in section.vehicle_set.all():
        if 'vehicles' not in section_json:
            section_json['vehicles'] = []
        section_json['vehicles'].append({"text": v.name, "relative": get_relative_str(v)})

    for v in section.realestate_set.all():
        if 'real_estates' not in section_json:
            section_json['real_estates'] = []
        r = {
            "square": v.square,
            "type_raw": "" if v.type is None else v.type,
            "owntype_raw": "" if v.owntype is None else v.own_type_str,
            "relative": get_relative_str(v),
            "country_raw": "" if v.country is None  else v.country_str
        }
        section_json['real_estates'].append(r)

    section_json['year'] = str(section.income_year)
    section_json['source'] = "disclosures"
    section_json['office'] = whitespace_remover(section.office.name)
    section_json['office_id'] = section.office.id

    return section_json
