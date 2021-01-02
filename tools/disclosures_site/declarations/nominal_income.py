from collections import namedtuple

YearIncome = namedtuple('YearIncome', ['year', 'nominal_income'])

#average by the following sources:
# https://ac.gov.ru/archive/files/publication/a/20967.pdf
# https://ac.gov.ru/uploads/2-Publications/rus_feb_2020.pdf
# https://ac.gov.ru/files/publication/a/11944.pdf


RUSSIAN_NOMINAL_INCOMES_YEARLY = [
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
    for i in range(len(RUSSIAN_NOMINAL_INCOMES_YEARLY)):
        if RUSSIAN_NOMINAL_INCOMES_YEARLY[i].year == year:
            return i
    return -1

IncomeCompare = namedtuple('IncomeCompare', ['population_income', 'declarant_income', 'min_year', 'max_year'])

#years are not continous
def get_average_nominal_incomes(years, incomes):
    if len(years) <= 1:
        return None
    first_declarant_income = None
    population_start_index = None
    last_declarant_income = None
    population_end_index = None
    for i in range(len(years)):
        if incomes[i] == 0 or incomes[i] is None:
            continue
        k = find_year(years[i])
        if k != -1:
            if first_declarant_income is None:
                population_start_index = k + 1
                first_declarant_income = incomes[i]
            last_declarant_income = incomes[i]
            population_end_index = k + 1
    if population_start_index is None or population_start_index == population_end_index:
        return None
    growth = 1.0
    for i in range(population_start_index, population_end_index):
        growth = growth + growth * RUSSIAN_NOMINAL_INCOMES_YEARLY[i].nominal_income
    declarant_growth = (float(last_declarant_income) - float(first_declarant_income)) / float(first_declarant_income)
    population_growth = growth - 1.0
    return IncomeCompare(int(100.0 * population_growth), \
           int(100.0 * declarant_growth), \
           RUSSIAN_NOMINAL_INCOMES_YEARLY[population_start_index].year, \
           RUSSIAN_NOMINAL_INCOMES_YEARLY[population_end_index - 1].year)