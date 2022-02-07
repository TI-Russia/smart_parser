from office_db.region_year_snapshot import TAllRegionStatsForOneYear, TRegionYearStats
from office_db.russian_regions import TRussianRegions
from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory
from office_db.declarant_group_stat_data import TGroupStatDataList
from office_db.year_income import TYearIncome
import operator

#таблица ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME взята из https://rosstat.gov.ru/folder/210/document/13396
#(Социально-экономические показатели Российской Федерации в 1991-2020 гг.) - это архив, из него надо взять файл "Ретро_2021_Раздел5"
# в этой таблице читаем строку "Среднедушевые денежные доходы населения (в месяц), руб.
# Объяснение, что такое "Среднедушевые денежные доходы" можно найти здесь
# https://www.gks.ru/bgd/regl/b12_14p/IssWWW.exe/Stg/d01/05-met.htm
# in RUR
ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME = {
    2000: 2281,
    2001: 3062,
    2002: 3947,
    2003: 5167,
    2004: 6399,
    2005: 8088,
    2006: 10155,
    2007: 12540,
    2008: 14864,
    2009: 16895,
    2010: 18958,
    2011: 20780,
    2012: 23221,
    2013: 25684,
    2014: 27412,
    2015: 30254,
    2016: 30865,
    2017: 31897,
    2018: 33266,
    2019: 35338,
    2020: 36073
}

#MROT is described in https://ru.wikipedia.org/wiki/%D0%9C%D0%B8%D0%BD%D0%B8%D0%BC%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9_%D1%80%D0%B0%D0%B7%D0%BC%D0%B5%D1%80_%D0%BE%D0%BF%D0%BB%D0%B0%D1%82%D1%8B_%D1%82%D1%80%D1%83%D0%B4%D0%B0_%D0%B2_%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D0%B8
#data are from https://base.garant.ru/10180093/
MROT = {
    2000: 132,
    2001: 200,
    2002: 405,
    2003: 600,
    2004:  600,
    2005: 800,
    2006: 1100,
    2007: 2300,
    2008: 2300,
    2009: 4330,
    2010: 4330,
    2011: 4611,
    2012: 4611,
    2013: 5205,
    2014: 5554,
    2015: 5965,
    2016: 7500,
    2017: 7800,
    2018: 10605,
    2019: 11280,
    2020: 12130,
    2021: 12792,
    2022: 13890
}

#https://ru.wikipedia.org/wiki/%D0%9D%D0%B0%D1%81%D0%B5%D0%BB%D0%B5%D0%BD%D0%B8%D0%B5_%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D0%B8
RUSSIA_POPULATION = {
2000:	146890128,
2001:	146303611,
2002:	145649334,
2003:	144963650,
2004:	144333586,
2005:	143801046,
2006:	143236582,
2007:	142862692,
2008:	142747535,
2009:	142737196,
2010:	142833502,
2011:	142865433,
2012:	143056383,
2013:	143347059,
2014:	143666931,
2015:	146267288,
2016:	146544710,
2017:	146804372,
2018:	146880432,
2019:	146780720,
2020:	146748590,
2021:	146171015
}

RUSSIA_MEDIAN_SALARY = {
    2019: 30458,
    2020: 32422
}


class TIncomeCompare:
    def __init__(self, population_income_growth, declarant_income_growth, min_year, max_year):
        self.population_income_growth = population_income_growth
        self.declarant_income_growth = declarant_income_growth
        self.min_year = min_year
        self.max_year = max_year

    def compare_to_all_people_income(self):
        return self.declarant_income_growth / self.population_income_growth


LAST_DECLARATION_YEAR = 2020


class TRussia:
    def __init__(self):
        self.regions = TRussianRegions()
        self.year_stat = dict()
        for year in [LAST_DECLARATION_YEAR]:
            self.init_one_year_stats(year)
        self.sorted_region_list_for_web_interface = self._build_region_list_for_combo_box()
        self.offices_in_memory = TOfficeTableInMemory()
        self.offices_in_memory.read_from_local_file()
        self.federal_fsin = self.offices_in_memory.fsin_by_region[TRussianRegions.Russia_as_s_whole_region_id]
        assert self.federal_fsin is not None
        self.office_stat = TGroupStatDataList(TGroupStatDataList.office_group)
        self.office_stat.load_from_disk()

        self.rubric_stat = TGroupStatDataList(TGroupStatDataList.rubric_group)
        self.rubric_stat.load_from_disk()

    def get_office(self, office_id) -> TOfficeInMemory:
        return self.offices_in_memory.get_office_by_id(office_id)

    def get_fsin_by_region(self, region_id) -> TOfficeInMemory:
        return self.offices_in_memory.fsin_by_region.get(region_id, self.federal_fsin)

    def iterate_offices(self) -> TOfficeInMemory:
        for office in self.offices_in_memory.offices.values():
            yield office

    def iterate_offices_ids(self):
        for office_id in self.offices_in_memory.offices.keys():
            yield office_id

    def init_one_year_stats(self, year):
        s = TAllRegionStatsForOneYear(year, regions=self.regions)
        s.load_from_disk()
        s.build_correlation_matrix()
        self.year_stat[year] = s
        if LAST_DECLARATION_YEAR == year:
            for r in self.regions.regions:
                if r.id == TRussianRegions.Russia_as_s_whole_region_id:
                    last_sala = max(RUSSIA_MEDIAN_SALARY.items(), key=operator.itemgetter(0))[1]
                    last_popul = max(RUSSIA_POPULATION.items(), key=operator.itemgetter(0))[1]
                    r.set_stat_data(TRegionYearStats(r.id, r.name, citizen_month_median_salary=last_sala,
                                     population=last_popul))
                else:
                    r.set_stat_data(s.get_region_info(r.id))

    #years are not continous but ordered by year
    def get_average_nominal_incomes(self, year_incomes) -> TIncomeCompare:
        if len(year_incomes) <= 1:
            return None
        first_income = None
        last_income = None
        for year_income in year_incomes:
            if year_income.income == 0 or year_income.income is None:
                continue
            if year_income.year not in MROT:
                continue
            if year_income.income < 12*MROT[year_income.year]:
                continue
            if year_income.year in ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME:
                if first_income is None:
                    first_income = year_income
                last_income = year_income
        if first_income is None or first_income == last_income:
            return None
        if first_income.year == last_income.year:
            return None
        declarant_growth = TYearIncome.get_income_diff(first_income.income, last_income.income)
        population_growth = TYearIncome.get_income_diff(ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME[first_income.year],
                                            ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME[last_income.year])
        return TIncomeCompare(population_growth, declarant_growth, first_income.year, last_income.year)

    def compare_to_all_russia_average_month_income(self, year: int, month_income):
        i = ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME.get(year)
        if i is None:
            return None
        return round(float(month_income) / float(i), 2)

    def get_mrot(self, year: int):
        return MROT.get(year)

    def _build_region_list_for_combo_box(self):
        lst = list()
        lst.append(('', ''))
        for r in self.regions.regions:
            name = r.name
            if len(name) > 33:
                name = name[:33]
            lst.append((r.id, name))
        lst.sort(key=operator.itemgetter(1))
        return lst

RUSSIA = TRussia()
