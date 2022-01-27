from collections import namedtuple


class YearIncome:
    def __init__(self, year, income):
        self.year = year
        self.income = income

    def __str__(self):
        return "YearIncome({},{})".format(self.year, self.income)

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

IncomeCompare = namedtuple('IncomeCompare', ['population_income', 'declarant_income', 'min_year', 'max_year'])


def get_income_diff(income1, income2):
    return int(100.0 * (float(income2) - float(income1)) / float(income1))

#years are not continous but ordered by year
def get_average_nominal_incomes(year_incomes):
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
    declarant_growth = get_income_diff(first_income.income, last_income.income)
    population_growth = get_income_diff(ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME[first_income.year],
                                        ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME[last_income.year])
    return IncomeCompare(population_growth, declarant_growth, first_income.year, last_income.year)
