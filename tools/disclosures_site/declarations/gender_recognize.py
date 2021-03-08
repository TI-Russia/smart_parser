from collections import defaultdict
from django.db import connection

from declarations.russian_fio import TRussianFio, POPULAR_RUSSIAN_NAMES


class TGender:
    masculine = 1
    feminine = 2

    @staticmethod
    def gender_list():
        return [TGender.masculine, TGender.feminine]

    @staticmethod
    def gender_to_str(gender_id):
        if gender_id == TGender.masculine:
            return "masculine"
        elif gender_id == TGender.feminine:
            return "feminine"
        else:
            return "None"

    @staticmethod
    def gender_to_Russian_str(gender_id):
        if gender_id == TGender.masculine:
            return "мужской"
        elif gender_id == TGender.feminine:
            return "женский"
        else:
            return "None"

    @staticmethod
    def opposite_gender(gender_id):
        if gender_id == TGender.masculine:
            return TGender.feminine
        elif gender_id == TGender.feminine:
            return TGender.masculine
        else:
            return None


class TGenderRecognizer:

    def __init__(self):
        self.names_masc = set()
        self.names_fem = set()
        self.surnames_masc = set()
        self.surnames_fem = set()

    def is_masculine_patronymic(self, s):
        return s.endswith("вич") or s.endswith("мич") or s.endswith("ьич")

    def is_feminine_patronymic(self, s):
        return s.endswith("вна") or s.endswith("чна")

    def build_masc_and_fem_names(self, max_count, filename):
        query = """
            select person_name 
            from declarations_person
            limit {}  
        """.format(max_count)
        names_fem_frq = defaultdict(int)
        names_masc_frq = defaultdict(int)
        surnames = defaultdict(int)
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_name, in cursor:
                fio = TRussianFio(person_name)
                if not fio.is_resolved:
                    continue
                if fio.family_name is not None and len(fio.first_name) > 1:
                    surnames[fio.family_name] += 1
                    gender = None
                    if self.is_feminine_patronymic(fio.patronymic):
                        gender = TGender.feminine
                    elif self.is_masculine_patronymic(fio.patronymic):
                        gender = TGender.masculine
                    elif fio.family_name[-1] == "а" or fio.family_name[-1] == "я":
                        gender = TGender.feminine
                    else:
                        gender = TGender.masculine

                    if gender == TGender.masculine:
                        names_masc_frq[fio.first_name] += 1
                    else:
                        names_fem_frq[fio.first_name] += 1

        self.names_masc.clear()
        self.names_fem.clear()
        with open(filename, "w") as outp:
            names = set(names_masc_frq.keys())
            names.update(names_fem_frq.keys())
            for name in names:
                all_name_freq = (names_fem_frq[name] + names_masc_frq[name])
                if 2 * all_name_freq < surnames[name]:
                    continue
                fem_ratio = int(100.0 * names_fem_frq[name] / float(all_name_freq))
                outp.write("{}\t{}\t{}\t{}\n".format(
                    name,
                    names_masc_frq[name],
                    names_fem_frq[name],
                    fem_ratio
                ))
                if fem_ratio > 90:
                    self.names_fem.add(name)
                if fem_ratio < 10:
                    self.names_masc.add(name)

    def build_masc_and_fem_surnames(self, max_count, filename):
        query = """
            select person_name 
            from declarations_person
            limit {}  
        """.format(max_count)

        surnames_fem_frq = defaultdict(int)
        surnames_masc_frq = defaultdict(int)
        surnames = defaultdict(int)
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_name, in cursor:
                fio = TRussianFio(person_name)
                if not fio.is_resolved:
                    continue
                if fio.first_name in self.names_masc:
                    surnames_masc_frq[fio.family_name] += 1
                if fio.first_name in self.names_fem:
                    surnames_fem_frq[fio.family_name] += 1
                surnames[fio.family_name] += 1

        self.surnames_masc.clear()
        self.surnames_fem.clear()
        with open(filename, "w") as outp:
            for surname in surnames:
                all_surname_freq = surnames_fem_frq[surname] + surnames_masc_frq[surname] + 0.00000001
                fem_ratio = int(100.0 * surnames_fem_frq[surname] / float(all_surname_freq))
                gender = None
                if surname.endswith("о") or surname.endswith("ук") or surname.endswith("юк") or surname.endswith("o") \
                        or surname.endswith("и"):
                    gender = None
                elif (all_surname_freq > 3 and fem_ratio > 90) or surname.endswith('ская') or surname.endswith('цкий'):
                    gender = TGender.feminine
                elif (all_surname_freq > 3 and fem_ratio < 10) or surname.endswith('ский') or surname.endswith('цкая'):
                    gender = TGender.masculine
                elif surname.endswith('а') and surnames_masc_frq[surname[:-1]] > 3:
                    #surname=иванова, search for иванов
                    gender = TGender.feminine
                elif not surname.endswith('а') and surnames_fem_frq[surname + 'а'] > 3:
                    # surname=иванов, search for иванова
                    gender = TGender.masculine
                elif len(surname) > 4 and (surname.endswith('ова') or surname.endswith('ева') \
                                           or surname.endswith('ёва') or surname.endswith('ина') or surname.endswith('ына')):
                    gender = TGender.feminine
                elif len(surname) > 4 and (surname.endswith('ов') or surname.endswith('ев') or surname.endswith('ёв') \
                        or surname.endswith('ин') or surname.endswith('ын')) and fem_ratio < 1:
                    gender = TGender.masculine
                if gender == TGender.masculine and (surname[-1] == "а" or surname[-1] == "я"):
                    gender = None
                outp.write("{}\t{}\t{}\t{}\t{}\n".format(
                    surname,
                    surnames_masc_frq[surname],
                    surnames_fem_frq[surname],
                    surnames[surname],
                    fem_ratio,
                    TGender.gender_to_str(gender)
                ))
                if gender is not None:
                    if gender == TGender.masculine:
                        self.surnames_masc.add(surname)
                    else:
                        self.surnames_fem.add(surname)

    def recognize_gender(self, fio):
        if len(fio.first_name) > 1 and fio.first_name in self.names_fem:
            return TGender.feminine
        if len(fio.first_name) > 1 and fio.first_name in self.names_masc:
            return TGender.masculine
        if fio.family_name in self.surnames_fem:
            return TGender.feminine
        if fio.family_name in self.surnames_masc:
            return TGender.masculine
        if self.is_feminine_patronymic(fio.patronymic):
            return TGender.feminine
        if self.is_masculine_patronymic(fio.patronymic):
            return TGender.masculine
        return None

    def recognize_gender_by_first_name(self, name):
        if len(name) > 1 and name in self.names_fem:
            return TGender.feminine
        if len(name) > 1 and name in self.names_masc:
            return TGender.masculine
        return None

    def build_person_gender_by_years_report(self, max_count, filename, start_year=2010, last_year=2019):
        query = """
            select p.id, p.person_name, min(s.income_year) 
            from declarations_section s
            join declarations_person p on s.person_id=p.id
            where s.person_id is not null and s.income_year > 2009
            group by s.person_id
            limit {}  
        """.format(max_count)
        masc = defaultdict(int)
        fem = defaultdict(int)
        with open(filename, "w") as outp:
            with connection.cursor() as cursor:
                cursor.execute(query)
                for person_id, person_name, min_year in cursor:
                    fio = TRussianFio(person_name)
                    if not fio.is_resolved:
                        continue

                    gender = self.recognize_gender(fio)
                    if start_year <= min_year <= last_year:
                        if gender == TGender.masculine:
                            masc[min_year] += 1
                        elif gender == TGender.feminine:
                            fem[min_year] += 1
                    outp.write("{}\t{}\t{}\n".format(
                        person_name,
                        min_year,
                        TGender.gender_to_str(gender)
                    ))
        #echo "select count(o.region_id), r.name from declarations_section s join declarations_source_document d on d.id=s.source_document_id join declarations_office o on o.id = d.office_id  join declarations_region r on r.id=o.region_id where s.person_name like '% миляуша %' group by o.region_id " | mysql -u disclosures -D disclosures_db -pdisclosures | sort -nr

        with open(filename + ".sum", "w") as outp:
            outp.write("year\tmasc\tfem\tfem_ratio\n")
            for year in range(start_year, last_year + 1):
                fam_ratio = round(100.0 * fem[year] / (fem[year] + masc[year]), 2)
                outp.write("{}\t{}\t{}\t{}\n".format(
                    year,
                    masc[year],
                    fem[year],
                    fam_ratio,
                ))
