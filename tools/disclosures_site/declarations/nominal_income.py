from collections import namedtuple


class YearIncome:
    def __init__(self, year, income):
        self.year = year
        self.income = income

#average by the following sources:
# https://ac.gov.ru/archive/files/publication/a/20967.pdf
# https://ac.gov.ru/uploads/2-Publications/rus_feb_2020.pdf
# https://ac.gov.ru/files/publication/a/11944.pdf


# must be without gaps
RUSSIAN_NOMINAL_INCOME_GROWTHS_YEARLY = [
    YearIncome(2010, 0.11),
    YearIncome(2011, 0.11),
    YearIncome(2012, 0.11),
    YearIncome(2013, 0.117),
    YearIncome(2014, 0.069),
    YearIncome(2015, 0.105),
    YearIncome(2016, 0.0151),
    YearIncome(2017, 0.025),
    YearIncome(2018, 0.041),
    YearIncome(2019, 0.061),
]

def find_year(year):
    for i in range(len(RUSSIAN_NOMINAL_INCOME_GROWTHS_YEARLY)):
        if RUSSIAN_NOMINAL_INCOME_GROWTHS_YEARLY[i].year == year:
            return i
    return -1

#таблица ROSSTAT_ALL_RUSSIA_AVERAGE_MONTH_INCOME взята из https://rosstat.gov.ru/folder/210/document/13396
#(Социально-экономические показатели Российской Федерации в 1991-2020 гг.) - это архив, из него надо взять файл "Ретро_2021_Раздел5"
# в этой таблице читаем строку "Среднедушевые денежные доходы населения (в месяц), руб.
# Объяснение, что такое "Среднедушевые денежные доходы" можно найти здесь
# https://www.gks.ru/bgd/regl/b12_14p/IssWWW.exe/Stg/d01/05-met.htm

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


IncomeCompare = namedtuple('IncomeCompare', ['population_income', 'declarant_income', 'min_year', 'max_year'])


#years are not continous but ordered by year
def get_average_nominal_incomes(year_incomes):
    if len(year_incomes) <= 1:
        return None
    first_declarant_income = None
    population_start_index = None
    last_declarant_income = None
    population_end_index = None
    for year_income in year_incomes:
        if year_income.income == 0 or year_income.income is None:
            continue
        k = find_year(year_income.year)
        if k != -1:
            if first_declarant_income is None:
                population_start_index = k + 1
                first_declarant_income = year_income.income
            last_declarant_income = year_income.income
            population_end_index = k + 1
    if population_start_index is None or population_start_index == population_end_index:
        return None
    growth = 1.0
    for i in range(population_start_index, population_end_index):
        growth = growth + growth * RUSSIAN_NOMINAL_INCOME_GROWTHS_YEARLY[i].income
    declarant_growth = (float(last_declarant_income) - float(first_declarant_income)) / float(first_declarant_income)
    population_growth = growth - 1.0
    return IncomeCompare(int(100.0 * population_growth), \
           int(100.0 * declarant_growth), \
           RUSSIAN_NOMINAL_INCOME_GROWTHS_YEARLY[population_start_index - 1].year, \
           RUSSIAN_NOMINAL_INCOME_GROWTHS_YEARLY[population_end_index - 1].year)