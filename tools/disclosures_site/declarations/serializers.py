from . import models
from common.primitives import normalize_whitespace
from declarations.countries import get_country_code
from django.db import connection
import re

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
                relative=models.Relative.get_relative_code( i.get('relative'))
            )


def convert_to_int_with_nones(v):
    if v is None:
        return 0
    return int(v)


class TSectionPassportFactory:
    AMBIGUOUS_KEY = "AMBIGUOUS_KEY"

    def __init__(self, office_id, year, person_name, income_sum, square_sum, vehicle_count, office_hierarchy=None):
        income_sum = str(convert_to_int_with_nones(income_sum))
        square_sum = str(convert_to_int_with_nones(square_sum))
        vehicle_count = str(convert_to_int_with_nones(vehicle_count))
        office_id = str(office_id)
        year = str(year)
        person_name = normalize_whitespace(person_name).lower()
        family_name = person_name.split(" ")[0]
        variants = [
             (office_id, year, person_name, income_sum, square_sum, vehicle_count), # the most detailed is the first
             (office_id, year, family_name, income_sum, square_sum, vehicle_count),
             (office_id, year, person_name, income_sum)
        ]
        if office_hierarchy is not None:
            parent_office_id = str(office_hierarchy.get_parent_office(office_id))
            if parent_office_id != office_id:
                variants.append((parent_office_id, year, person_name, income_sum, square_sum, vehicle_count))
                variants.append((parent_office_id, year, family_name, income_sum)) #t is the most abstract passport parent office and family_name

        self.passport_variants = list(map((lambda x: "\t".join(x)), variants))

    @staticmethod
    def get_all_passport_factories(office_hierarchy=None):
        # section_id  and all 6 passport components
        # see https://stackoverflow.com/questions/2436284/mysql-sum-for-distinct-rows for arithmetics explanation
        query = """select  s.id, 
                         d.office_id, 
                         sum(i.size) * count(distinct i.id) / count(*),
                         s.person_name, 
                         s.income_year,
                         sum(r.square) * count(distinct r.id) / count(*),
                         count(distinct v.id)
                from {} s
                inner join {} d on s.source_document_id = d.id
                left  join {} i on i.section_id = s.id
                left  join {} r on r.section_id = s.id
                left  join {} v on v.section_id = s.id
                group by s.id
                """.format(
                        models.Section.objects.model._meta.db_table,
                        models.Source_Document.objects.model._meta.db_table,
                        models.Income.objects.model._meta.db_table,
                        models.RealEstate.objects.model._meta.db_table,
                        models.Vehicle.objects.model._meta.db_table
                )
        with connection.cursor() as cursor:
            cursor.execute(query)
            for section_id, office_id, income_sum, person_name, year, square_sum, vehicle_count in cursor.fetchall():
                yield section_id, TSectionPassportFactory(office_id, year, person_name, income_sum,
                                                              income_sum, vehicle_count, office_hierarchy=office_hierarchy)

    @staticmethod
    def get_all_passports_dict(iterator):
        passport_to_id = dict()
        for (id, passport_factory) in iterator:
            for passport in passport_factory.get_passport_collection():
                search_result = passport_to_id.get(passport)
                if search_result is None:
                    passport_to_id[passport] = id
                elif search_result != id: #ignore the same passport
                    passport_to_id[passport] = TSectionPassportFactory.AMBIGUOUS_KEY
        return passport_to_id

    def get_passport_collection(self):
        return self.passport_variants

    def search_by_passports(self, all_passports):
        search_results = list()
        res = None
        for passport in self.passport_variants:
            res = all_passports.get(passport)
            if res is not None and res != TSectionPassportFactory.AMBIGUOUS_KEY:
                return res, search_results
            search_results.append(res)

        if res == TSectionPassportFactory.AMBIGUOUS_KEY:
            res = None
        return res, search_results


def normalize_fio(fio):
    fio = normalize_whitespace(fio)
    fio = fio.replace('"', ' ').strip()
    return fio.title()


class TSmartParserJsonReader:

    class SerializerException(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)

    def __init__(self, income_year, source_document, section_json, id=None):
        self.section_json = section_json
        self.section = models.Section(
            source_document=source_document,
            income_year=income_year,
        )
        self.init_person_info()
        self.incomes = list(read_incomes(section_json))
        self.real_estates = list(read_real_estates(section_json))
        self.vehicles = list(read_vehicles(section_json))

    def init_person_info(self):
        person_info = self.section_json.get('person')
        if person_info is None:
            fio = self.section_json.get('fio')
            if fio is None:
                raise TSmartParserJsonReader.SerializerException("cannot find nor 'person' neither 'fio' key in json")
        else:
            fio = person_info.get('name', person_info.get('name_raw'))
            if fio is None:
                raise TSmartParserJsonReader.SerializerException("cannot find 'name' or 'name_raw'in json")
        self.section.person_name = normalize_fio(fio)
        self.section.position = person_info.get("role")
        self.section.department = person_info.get("department")

    def get_passport_factory(self, office_hierarchy=None):
        return TSectionPassportFactory(
                    self.section.source_document.office.id,
                    self.section.income_year,
                    self.section.person_name,
                    sum(convert_to_int_with_nones(i.size) for i in self.incomes),
                    sum(convert_to_int_with_nones(r.square) for r in self.real_estates),
                    sum(1 for v in self.vehicles),
                    office_hierarchy=office_hierarchy)

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
    section_json['office'] = whitespace_remover(section.source_document.office.name)
    section_json['office_id'] = section.source_document.office.id

    return section_json
