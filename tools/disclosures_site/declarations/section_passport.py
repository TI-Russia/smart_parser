from common.primitives import normalize_whitespace
from declarations import models

from django.db import connection


def convert_to_int_with_nones(v):
    if v is None:
        return 0
    return int(v)


class TSectionPassportItems1:
    def __init__(self, office_id, year, person_name, income_sum, square_sum, vehicle_count):
        self.income_sum = str(convert_to_int_with_nones(income_sum))
        self.square_sum = str(convert_to_int_with_nones(square_sum))
        self.vehicle_count = str(convert_to_int_with_nones(vehicle_count))
        self.office_id = str(office_id)
        self.year = str(year)
        self.person_name = normalize_whitespace(person_name).lower()

    def get_main_section_passport(self):
        return ";".join((self.office_id,
                         self.year,
                         self.person_name,
                         self.income_sum,
                         self.square_sum,
                         self.vehicle_count)) # the most detailed passport

    def get_all_passport_variants_for_toloka_pool(self, office_hierarchy):
        family_name = self.person_name.split(" ")[0]
        variants = [
             (self.office_id, self.year, self.person_name, self.income_sum, self.square_sum, self.vehicle_count), # the most detailed is the first
             (self.office_id, self.year, family_name, self.income_sum, self.square_sum, self.vehicle_count),
             (self.office_id, self.year, self.person_name, self.income_sum)
        ]
        parent_office_id = str(office_hierarchy.get_top_parent_office_id(self.office_id))
        if parent_office_id != self.office_id:
            variants.append((parent_office_id, self.year, self.person_name, self.income_sum, self.square_sum, self.vehicle_count))
            variants.append((parent_office_id, self.year, family_name, self.income_sum)) #it is the most abstract passport parent office and family_name
        return list(map((lambda x: "\t".join(x)), variants))

    @staticmethod
    def get_section_passport_components():
        # section_id  and all 6 passport components
        # see https://stackoverflow.com/questions/2436284/mysql-sum-for-distinct-rows for arithmetics explanation
        query = """select  s.id, 
                         s.office_id, 
                         sum(i.size) * count(distinct i.id) / count(*),
                         s.person_name, 
                         s.income_year,
                         sum(r.square) * count(distinct r.id) / count(*),
                         count(distinct v.id)
                from declarations_section s
                left  join declarations_income i on i.section_id = s.id
                left  join declarations_realestate r on r.section_id = s.id
                left  join declarations_vehicle v on v.section_id = s.id
                group by s.id
                """
        with connection.cursor() as cursor:
            cursor.execute(query)
            for section_id, office_id, income_sum, person_name, year, square_sum, vehicle_count in cursor.fetchall():
                yield section_id, TSectionPassportItems1(office_id, year, person_name, income_sum,
                                                        square_sum, vehicle_count)
        cursor.close()


# Основные паспорта секций TSectionPassportItems1 сделаны не зависимыми от номеров документов.
# Это позволяет эффективно работать с дублями  документов (уточнениями документов).
# Но когда мы меняем сам smart_parser, резко меняются количество приписанных машин и недвижимости, из-за этого
# основные паспорта секций перестают работать.  Придется сделать дополнительные паспорта (TSectionPassportItems2),
# которые привязаны к документу, но содержат меньше подробностей. Дополнительные паспорта фактически построены так же,
# как паспорта, которые используются в copy_person_id. Этот комментарий надо добавить в html-описание.
class TSectionPassportItems2:
    def __init__(self, document_id, year, person_name, income_sum):
        self.document_id = str(document_id)
        self.year = str(year)
        self.person_name = normalize_whitespace(person_name).lower()
        self.income_sum = str(convert_to_int_with_nones(income_sum))

    def get_main_section_passport(self):
        return ";".join((self.document_id,
                         self.year,
                         self.person_name,
                         self.income_sum
                         ))  # the most detailed passport


    @staticmethod
    def get_section_passport_components():
        # see https://stackoverflow.com/questions/2436284/mysql-sum-for-distinct-rows for arithmetics explanation
        query = """select  s.id, 
                           s.source_document_id, 
                           sum(i.size) * count(distinct i.id) / count(*),
                           s.person_name, 
                           s.income_year
                        from declarations_section s
                        left  join declarations_income i on i.section_id = s.id
                        group by s.id
               """

        with connection.cursor() as cursor:
            cursor.execute(query)
            for section_id, document_id, income_sum, person_name, year in cursor.fetchall():
                yield section_id, TSectionPassportItems2(document_id, year, person_name, income_sum)
        cursor.close()

