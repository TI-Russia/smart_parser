from django.db import models
from django.utils.translation import  get_language
from .countries import get_country_str
from .rubrics import get_russian_rubric_str
from declarations.nominal_income import get_average_nominal_incomes, YearIncome
from declarations.ratings import TPersonRatings
from declarations.car_brands import CAR_BRANDS
from common.urllib_parse_pro import urlsplit_pro

from collections import defaultdict
from operator import attrgetter
from itertools import groupby
import os


def get_django_language():
    lang = get_language().lower()
    if len(lang) > 2:
        lang = lang[:2]
    return lang


def russian_numeral_group(num, singular_nominativ, singular_genitiv, plural_genitiv):
    if num is None:
        return ""
    s = str(num)
    if len(s) == 0:
        return ""
    if len(s) > 1 and s[-2] == '1':       #10, 11, 12, ...,19, 110, 111...
        return plural_genitiv
    elif s[-1] == "1":                    #1, 21, 31, 41, 101, 121, ...201, ...
        return singular_nominativ
    elif s[-1] == "2" or s[-1] == "3" or s[-1] == "4":    # 2, 3, 4, 22, 23, 24, 32, 33...
        return singular_genitiv
    else:
        return plural_genitiv         # 5,6,7,8,9,...,25,26,27....



class Region(models.Model):
    name = models.TextField(verbose_name='region name')
    wikibase_id = models.CharField(max_length=10, null=True)


class SynonymClass:
    Russian = 0
    English = 1
    EnglishShort = 2
    RussianShort = 3


class Region_Synonyms(models.Model):
    region = models.ForeignKey('declarations.Region', verbose_name="region", on_delete=models.CASCADE)
    synonym = models.TextField(verbose_name='region synonym')
    synonym_class = models.IntegerField(null=True) #see SynonymClass


class Office(models.Model):
    name = models.TextField(verbose_name='office name')
    region = models.ForeignKey('declarations.Region', verbose_name="region", on_delete=models.CASCADE, null=True)
    type_id = models.IntegerField(null=True)
    parent_id = models.IntegerField(null=True)
    rubric_id = models.IntegerField(null=True, default=None) # see TOfficeRubrics
    calculated_params = models.JSONField(null=True, default=None)

    @property
    def source_document_count(self):
        try:
            return self.source_document_set.all().count()
        except Exception as exp:
            raise

    @property
    def region_name(self):
        if self.region is None:
            return ""

        try:
            return self.region.name
        except Exception as exp:
            raise

    @property
    def source_document_count_html(self):
        num = self.calculated_params['source_document_count']
        s = "{} {}".format(num, russian_numeral_group(num, "документ", "документа", "документов"))
        return s

    @property
    def section_count_html(self):
        num = self.calculated_params['section_count']
        s = "{} {}".format(num, russian_numeral_group(num, "декларация", "декларации", "деклараций"))
        return s

    @property
    def section_count_by_years_html(self):
        data = self.calculated_params['section_count_by_years']
        html = "<table class=\"section_by_count\"> <tr> "
        for year in data.keys():
            html += "<th>{}</th>".format(year)
        html += "</tr><tr>"
        for year, cnt in data.items():
            html += "<td><a href=\"/section?office_id={}&income_year={}\">{}</a></td>".format(self.id, year, cnt)
        html += "</tr></table>"
        return html

    @property
    def urls_html(self):
        pairs = ((u, urlsplit_pro(u).netloc) for u in self.calculated_params['urls'])
        return "&nbsp;&nbsp;&nbsp;".join('<a href="{}">{}</a>'.format(url, anchor) for url, anchor in pairs)

    @property
    def parent_office_name(self):
        if self.parent_id is None:
            return ""
        return Office.objects.get(pk=self.parent_id).name

    @property
    def rubric_str(self):
        if self.rubric_id is None:
            return "unknown"
        else:
            return get_russian_rubric_str(self.rubric_id)


class Relative:
    main_declarant_code = "D"
    spouse_code = "S"
    child_code = "C"
    unknown_code = "?"
    code_to_info = dict()
    lower_russian_to_code = dict()

    @staticmethod
    def get_relative_code(russian_name):
        if russian_name is None:
            return Relative.main_declarant_code
        r = russian_name.strip(" \n\r\t").lower()
        return Relative.lower_russian_to_code.get(r, Relative.unknown_code)

    @staticmethod
    def static_initalize():
        Relative.code_to_info = {
            Relative.main_declarant_code:  {"ru": "", "en": "", "visual_order": 0},  # main public servant
            Relative.spouse_code: {"ru": "супруг(а)", "en": "spouse", "visual_order": 1},
            Relative.child_code: {"ru": "ребенок", "en": "child", "visual_order": 2},
            Relative.unknown_code: {"ru": "иное", "en": "other", "visual_order": 3},
        }
        Relative.lower_russian_to_code = dict(((value['ru'].lower(), key) for key, value in Relative.code_to_info.items()))

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
    using_code = "U"
    code_to_info = dict()
    lower_russian_to_code = dict()

    @staticmethod
    def get_own_type_code(russian_name):
        if russian_name is None:
            return OwnType.property_code
        r = russian_name.strip(" \n\r\t").lower()
        return OwnType.lower_russian_to_code.get(r, OwnType.property_code)


    @staticmethod
    def static_initalize():
        OwnType.code_to_info = {
            OwnType.property_code: {"ru": "В собственности", "en": "private"},
            OwnType.using_code: {"ru": "В пользовании", "en": "in use"},
            "?": {"ru": "иное", "en": "other"},
        }
        OwnType.lower_russian_to_code = dict((value['ru'].lower(), key) for key, value in OwnType.code_to_info.items())


OwnType.static_initalize()


class Web_Reference(models.Model):
    source_document = models.ForeignKey('declarations.source_document', verbose_name="source document", on_delete=models.CASCADE)
    dlrobot_url = models.TextField(null=True)
    crawl_epoch = models.IntegerField(null=True)
    web_domain = models.TextField(null=True)


class Declarator_File_Reference(models.Model):
    source_document = models.ForeignKey('declarations.source_document', verbose_name="source document",
                                 on_delete=models.CASCADE)
    declarator_documentfile_id = models.IntegerField(null=True)
    declarator_document_id = models.IntegerField(null=True)
    declarator_document_file_url = models.TextField(null=True)
    web_domain = models.TextField(null=True)


class Source_Document(models.Model):
    id = models.IntegerField(primary_key=True)
    office = models.ForeignKey('declarations.Office', verbose_name="office name", on_delete=models.CASCADE)
    sha256 = models.CharField(max_length=200)
    file_extension = models.CharField(max_length=16)
    intersection_status = models.CharField(max_length=16)

    # calculated fields (from sql table section)
    min_income_year = models.IntegerField(null=True, default=None)
    max_income_year = models.IntegerField(null=True, default=None)
    section_count = models.IntegerField(null=True, default=0)
    median_income = models.IntegerField(null=True, default=0)

    def get_permalink_passport(self):
        return "sd;{}".format(self.sha256)


class Person(models.Model):
    id = models.IntegerField(primary_key=True)
    person_name = models.CharField(max_length=64, verbose_name='person name')
    declarator_person_id = models.IntegerField(null=True)

    @property
    def section_count(self):
        return self.section_set.all().count()

    @property
    def last_section(self):
        return max( (s for s in self.section_set.all()), key=attrgetter("income_year"))

    @property
    def last_position_and_office_str(self):
        return self.last_section.position_and_office_str

    @property
    def declaraion_count_str(self):
        cnt = len(self.section_set.all())
        if cnt == 1:
            return "{} декларация".format(cnt)
        elif cnt < 5:
            return "{} декларации".format(cnt)
        else:
            return "{} деклараций".format(cnt)

    @property
    def has_spouse(self):
        for s in self.section_set.all():
            if s.has_spouse():
                return True
        return False

    @property
    def years_str(self):
        years = list(set(s.income_year for s in self.section_set.all()))
        years.sort()
        if len(years) == 1:
            return "{} год".format(years[0])
        else:
            return "{} годы".format(", ".join(map(str, years)))

    @property
    def sections_ordered_by_year(self):
        sections = list()
        for _, year_sections in groupby(sorted(self.section_set.all(), key=attrgetter("income_year")), key=attrgetter("income_year")):
            for s in year_sections:
                sections.append(s) # one section per year
                break
        return sections

    def income_growth_yearly(self):
        incomes = list()
        for s in self.sections_ordered_by_year:
            incomes.append(YearIncome(s.income_year, s.get_declarant_income_size()))
        return get_average_nominal_incomes(incomes)

    def get_permalink_passport(self):
        if self.declarator_person_id is not None:
            return "psd;" + str(self.declarator_person_id)
        else:
            return None

    @property
    def ratings(self):
        s = ""
        for r in self.person_rating_items_set.all():
            if r.rating.id == TPersonRatings.LuxuryCarRating:
                image_path = CAR_BRANDS.get_image_url(str(r.rating_value))
                rating_info = ""
            else:
                image_path = os.path.join("/static/images/", r.rating.image_file_path)
                rating_info = ", {} место, {} {}, число участников:{}".format(
                    r.person_place,
                    r.rating_value,
                    r.rating.rating_unit_name,
                    r.competitors_number
                )
            rating = '<abbr title="{} ({} год {})"> <image src="{}"/></abbr>'.format(
                r.rating.name,
                r.rating_year,
                rating_info,
                image_path)
            rating = "<a href={}>{}</a>".format(TPersonRatings.get_search_params_by_rating(r), rating)
            s += rating
        return s


class PersonRedirect(models.Model):
    id = models.IntegerField(primary_key=True)     # old person id, not existing in the database
    new_person_id = models.IntegerField()


class RealEstate(models.Model):
    section = models.ForeignKey('declarations.Section', on_delete=models.CASCADE)
    type = models.TextField(verbose_name='real_estate')
    country = models.CharField(max_length=2)
    relative = models.CharField(max_length=1)
    owntype = models.CharField(max_length=1)
    square = models.IntegerField(null=True)
    share = models.FloatField(null=True)
    relative_index = models.PositiveSmallIntegerField(null=True, default=None)

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
    relative_index = models.PositiveSmallIntegerField(null=True, default=None)
    name = models.TextField()


class Income(models.Model):
    section = models.ForeignKey('declarations.Section', on_delete=models.CASCADE)
    size = models.IntegerField(null=True)
    relative = models.CharField(max_length=1)
    relative_index = models.PositiveSmallIntegerField(null=True, default=None)


def get_distinct_relative_types(records):
    return set(Relative(x.relative) for x in records.all())


#https://ru.wikipedia.org/wiki/%D0%94%D0%B5%D1%81%D1%8F%D1%82%D0%B8%D1%87%D0%BD%D1%8B%D0%B9_%D1%80%D0%B0%D0%B7%D0%B4%D0%B5%D0%BB%D0%B8%D1%82%D0%B5%D0%BB%D1%8C
def format_income_in_html(income):
    if income is None:
        return 'null'
    s = "{:_.0f}".format(income).replace('_', '&nbsp;')
    s += " " + russian_numeral_group(income, "рубль", "рубля", "рублeй")
    return s


def format_realty_square_in_html(square_sum):
    if square_sum is None or square_sum == 0:
        return ""
    return "{} кв.м.".format(square_sum)


class Section(models.Model):
    id = models.IntegerField(primary_key=True)
    source_document = models.ForeignKey('declarations.source_document', null=True, verbose_name="source document", on_delete=models.CASCADE)
    person = models.ForeignKey('declarations.Person', null=True, verbose_name="person id", on_delete=models.CASCADE)
    person_name = models.CharField(max_length=64, verbose_name='person name')
    income_year = models.IntegerField(null=True)
    department = models.TextField(null=True)
    position = models.TextField(null=True)
    dedupe_score = models.FloatField(blank=True, null=True, default=0.0)
    surname_rank = models.IntegerField(null=True)
    name_rank = models.IntegerField(null=True)
    gender = models.PositiveSmallIntegerField(null=True, default=None)

    # sometimes Section.rubric_id overrides Office.rubric_id, see function convert_municipality_to_education for example
    rubric_id = models.IntegerField(null=True, default=None)

    @property
    def section_parts(self):
        relatives = set()
        relatives.add(Relative(Relative.main_declarant_code))
        relatives |= get_distinct_relative_types(self.income_set)
        relatives |= get_distinct_relative_types(self.realestate_set)
        relatives |= get_distinct_relative_types(self.vehicle_set)
        relative_list = Relative.sort_by_visual_order(list(relatives))
        return relative_list

    def get_surname_rank(self):
        return self.surname_rank if self.surname_rank is not None else 100

    def get_name_rank(self):
        return self.name_rank if self.name_rank is not None else 100

    def get_declarant_income_size(self):
        if hasattr(self, "tmp_income_set"):
            incomes = self.tmp_income_set # used during the main section import
        else:
            incomes = self.income_set.all()
        for i in incomes:
            if i.relative == Relative.main_declarant_code:
                return i.size
        return 0

    def get_spouse_income_size(self):
        for i in self.income_set.all():
            if i.relative == Relative.spouse_code:
                if i.size is None:
                    return None
                else:
                    return i.size
        return None

    @property
    def declarant_income_size_in_html(self):
        return format_income_in_html(self.get_declarant_income_size())

    @property
    def spouse_income_size_html(self):
        i = self.get_spouse_income_size()
        if i is None or i == 0:
            return ""
        return format_income_in_html(i)

    def get_permalink_passport(self):
        main_income = self.get_declarant_income_size()
        return "sc;{};{};{};{}".format(self.source_document.id, self.person_name.lower(), self.income_year, main_income)

    @property
    def rubric_str(self):
        if self.rubric_id is None:
            return "unknown"
        else:
            return get_russian_rubric_str(self.rubric_id)

    @staticmethod
    def describe_realty(r: RealEstate):
        if r is None:
            return ["", "", ""]
        type_str = r.type
        if r.country != "RU":
            type_str += " ({})".format(r.country_str)
        square_str = "none" if r.square is None else format_realty_square_in_html(r.square)
        return [type_str, square_str, r.own_type_str]

    @property
    def declarant_realty_square_sum_html(self):
        sum = 0
        cnt = 0
        for r in self.realestate_set.all():
            if r.relative == Relative.main_declarant_code:
                if r.square is not None:
                    sum += r.square
                    cnt += 1
        if cnt > 0 and sum > 0:
            return format_realty_square_in_html(sum)
        else:
            return ""

    @property
    def spouse_realty_square_sum_html(self):
        sum = 0
        has_realty = 0
        for r in self.realestate_set.all():
            if r.relative == Relative.spouse_code:
                if r.square is not None:
                    sum += r.square
                    has_realty = True
        if has_realty:
            return format_realty_square_in_html(sum)
        else:
            return ""

    @property
    def vehicle_count(self):
        return len(list(self.vehicle_set.all()))

    def has_spouse(self):
        for r in self.realestate_set.all():
            if r.relative == Relative.spouse_code:
                return True
        for r in self.income_set.all():
            if r.relative == Relative.spouse_code:
                return True
        for r in self.vehicle_set.all():
            if r.relative == Relative.spouse_code:
                return True
        return False

    @property
    def position_and_department(self):
        position_and_department = ""
        if self.department is not None:
            position_and_department += self.department

        if self.position is not None:
            if position_and_department != "":
                position_and_department += ", "
            position_and_department += self.position
        return position_and_department.strip()

    @property
    def office_name(self):
        return self.source_document.office.name

    @property
    def position_and_office_str(self):
        str = self.source_document.office.name
        position_and_department = self.position_and_department
        if position_and_department != "":
            str += " ({})".format(position_and_department)
        return str

    def get_html_table_header(self, has_vehicles):
        tr1 = ['<th rowspan="2">ФИО</th>', '<th colspan="3">Недвижимость</th>']
        if has_vehicles:
            tr1.append('<th rowspan="2">Транспорт</th>')
        tr1.append('<th rowspan="2" width="10%">Доход</th>')
        yield tr1
        yield ['<th>Тип</th>', '<th>Площадь</th>', '<th>Владение</th>']

    @property
    def html_table_data_rows(self):
        section_parts = self.section_parts

        realties = defaultdict(list)
        for r in self.realestate_set.all():
            realties[r.relative].append(Section.describe_realty(r))
        for x in section_parts:
            if len(realties[x.code]) == 0:
                realties[x.code].append(Section.describe_realty(None))

        vehicles = defaultdict(str)
        for v in self.vehicle_set.all():
            vehicles[v.relative] += v.name + "<br/>"

        incomes = defaultdict(str)
        for i in self.income_set.all():
            incomes[i.relative] = '<h3>' + format_income_in_html(i.size) + '</h3>'
        has_vehicles = len(vehicles.keys()) > 0
        table = list(self.get_html_table_header(has_vehicles))
        for relative in section_parts:
            cnt = 0
            for (realty_type, realty_square, own_type) in realties[relative.code]:
                if cnt == 0:
                    rowspan = len(realties[relative.code])
                    if relative.code == Relative.main_declarant_code:
                        cells = [(self.person_name, rowspan)]
                    else:
                        cells = [(relative.name, rowspan)]
                    cells.extend([(realty_type, 1), (realty_square, 1), (own_type, 1)])
                    if has_vehicles:
                        cells.append((vehicles[relative.code], rowspan))
                    cells.append((incomes[relative.code], rowspan))
                else:
                    cells = [(realty_type, 1), (realty_square, 1), (own_type, 1)]
                cnt += 1
                tds = list("<td rowspan=\"{}\">{}</td>".format(rowspan, value) for value, rowspan in cells)
                table.append(tds)
        return table

    def get_car_brands(self):
        car_brands = set()
        for v in self.vehicle_set.all():
            if v.name is not None and len(v.name) > 1:
                car_brands.update(CAR_BRANDS.find_brands(v.name))
        return list(car_brands)


class Person_Rating(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(verbose_name='rating name')
    image_file_path = models.TextField(verbose_name='file path')
    rating_unit_name = models.TextField(verbose_name='rating_unit')

    @staticmethod
    def create_ratings():
        Person_Rating(
            id=TPersonRatings.MaxDeclarantOfficeIncomeRating,
            name="Самый высокий доход внутри ведомства",
            image_file_path="declarant_office_income.png",
            rating_unit_name="руб.",
            ).save()

        Person_Rating(
            id=TPersonRatings.MaxSpouseOfficeIncomeRating,
            name="Самый высокий доход супруги(а) внутри ведомства",
            image_file_path="spouse_office_income.png",
            rating_unit_name= "руб.",
            ).save()

        Person_Rating(
            id=TPersonRatings.LuxuryCarRating,
            name="Дорогой автомобиль",
            image_file_path="",
            rating_unit_name="",
            ).save()


class Person_Rating_Items(models.Model):
    rating = models.ForeignKey('declarations.Person_Rating', on_delete=models.CASCADE)
    person = models.ForeignKey('declarations.Person', on_delete=models.CASCADE)
    person_place = models.IntegerField()
    rating_year = models.IntegerField()
    rating_value = models.IntegerField()
    competitors_number = models.IntegerField(default=0)
    office = models.ForeignKey('declarations.Office', on_delete=models.CASCADE, null=True)
