from django.test import TestCase, tag
from declarations.all_russia_stat_info import get_average_nominal_incomes, YearIncome


class NominalIncome(TestCase):
    @tag('front', 'central')
    def test_nominal_income(self):
        # out of year scope
        self.assertIsNone(get_average_nominal_incomes([YearIncome(2008, 1), YearIncome(2009, 2)]))

        # one year is not enough
        self.assertIsNone(get_average_nominal_incomes([YearIncome(2015,1)]))

        # two years
        comp = get_average_nominal_incomes([YearIncome(2015, 1000000), YearIncome(2016, 2000000)])
        self.assertEqual(comp.declarant_income, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income, 2)
        self.assertEqual(comp.min_year, 2015)
        self.assertEqual(comp.max_year, 2016)

        # 3 years
        comp = get_average_nominal_incomes([YearIncome(2015, 1000000), YearIncome(2016, 1500000), YearIncome(2017, 2000000)])
        self.assertEqual(comp.declarant_income, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income, 5, places=3)
        self.assertEqual(comp.min_year, 2015)
        self.assertEqual(comp.max_year, 2017)

        #2040  year is ignored
        comp = get_average_nominal_incomes([YearIncome(2015, 1000000), YearIncome(2016, 1500000), YearIncome(2017, 2000000),
                                            YearIncome(2040, 30000000)])
        self.assertEqual(comp.declarant_income, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income, 5, places=3)
        self.assertEqual(comp.min_year, 2015)
        self.assertEqual(comp.max_year, 2017)

        #1990     year is ignored
        comp = get_average_nominal_incomes([YearIncome(1990, 100000000), YearIncome(2015, 1000000),
                                            YearIncome(2016, 1500000), YearIncome(2017, 2000000)])
        self.assertEqual(comp.declarant_income, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income, 5, places=3)  # 4.5% growth
        self.assertEqual(comp.min_year, 2015)
        self.assertEqual(comp.max_year, 2017)

        #zero income is ignored
        comp = get_average_nominal_incomes([YearIncome(2015, 0), YearIncome(2016, 1500000), YearIncome(2017, 2000000)])
        self.assertAlmostEqual(comp.declarant_income, 33, places=3)  # 33% growth
        self.assertAlmostEqual(comp.population_income, 3, places=3)  # 3% growth of 2017
        self.assertEqual(comp.min_year, 2016)
        self.assertEqual(comp.max_year, 2017)

        #incomes less than 12*MROT are ignored
        incomes = [YearIncome(2012, 600), YearIncome(2013, 189744), YearIncome(2019, 407711)]
        comp = get_average_nominal_incomes(incomes)
        self.assertAlmostEqual(comp.declarant_income, 114, places=3)
        self.assertAlmostEqual(comp.population_income, 37, places=3)
        self.assertEqual(comp.min_year, 2013)
        self.assertEqual(comp.max_year, 2019)

        #real example 1
        incomes = [YearIncome(2012,1693027),YearIncome(2013,2790949),YearIncome(2017,4993935),YearIncome(2019,6241840)]
        comp = get_average_nominal_incomes(incomes)
        self.assertAlmostEqual(comp.declarant_income, 268, places=3)
        self.assertAlmostEqual(comp.population_income, 52   , places=3)
        self.assertEqual(comp.min_year, 2012)
        self.assertEqual(comp.max_year, 2019)

        #real example 2
        incomes = [YearIncome(2012,783050),YearIncome(2013,819684),YearIncome(2014,692259),YearIncome(2015,736241),YearIncome(2016,780312),YearIncome(2017,817646),YearIncome(2018,817078),YearIncome(2019,886266)]
        comp = get_average_nominal_incomes(incomes)
        self.assertAlmostEqual(comp.declarant_income, 13, places=3)
        self.assertAlmostEqual(comp.population_income, 52, places=3)
        self.assertEqual(comp.min_year, 2012)
        self.assertEqual(comp.max_year, 2019)

        #real example 3
        incomes = [YearIncome(2012,297096),YearIncome(2013,856340),YearIncome(2014,820063),YearIncome(2015,730649),YearIncome(2016,706835)]
        comp = get_average_nominal_incomes(incomes)
        self.assertAlmostEqual(comp.declarant_income, 137, places=3)
        self.assertAlmostEqual(comp.population_income, 32, places=3)
        self.assertEqual(comp.min_year, 2012)
        self.assertEqual(comp.max_year, 2016)
