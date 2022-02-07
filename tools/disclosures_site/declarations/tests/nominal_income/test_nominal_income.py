from django.test import TestCase, tag
from office_db.russia import RUSSIA, TYearIncome


class NominalIncome(TestCase):
    @tag('front', 'central')
    def test_nominal_income(self):
        # out of year scope
        self.assertIsNone(RUSSIA.get_average_nominal_incomes([TYearIncome(2008, 1), TYearIncome(2009, 2)]))

        # one year is not enough
        self.assertIsNone(RUSSIA.get_average_nominal_incomes([TYearIncome(2015,1)]))

        # two years
        comp = RUSSIA.get_average_nominal_incomes([TYearIncome(2015, 1000000), TYearIncome(2016, 2000000)])
        self.assertEqual(comp.declarant_income_growth, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income_growth, 2)
        self.assertEqual(comp.min_year, 2015)
        self.assertEqual(comp.max_year, 2016)

        # 3 years
        comp = RUSSIA.get_average_nominal_incomes([TYearIncome(2015, 1000000), TYearIncome(2016, 1500000), TYearIncome(2017, 2000000)])
        self.assertEqual(comp.declarant_income_growth, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income_growth, 5, places=3)
        self.assertEqual(comp.min_year, 2015)
        self.assertEqual(comp.max_year, 2017)

        #2040  year is ignored
        comp = RUSSIA.get_average_nominal_incomes([TYearIncome(2015, 1000000), TYearIncome(2016, 1500000), TYearIncome(2017, 2000000),
                                            TYearIncome(2040, 30000000)])
        self.assertEqual(comp.declarant_income_growth, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income_growth, 5, places=3)
        self.assertEqual(comp.min_year, 2015)
        self.assertEqual(comp.max_year, 2017)

        #1990     year is ignored
        comp = RUSSIA.get_average_nominal_incomes([TYearIncome(1990, 100000000), TYearIncome(2015, 1000000),
                                            TYearIncome(2016, 1500000), TYearIncome(2017, 2000000)])
        self.assertEqual(comp.declarant_income_growth, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income_growth, 5, places=3)  # 4.5% growth
        self.assertEqual(comp.min_year, 2015)
        self.assertEqual(comp.max_year, 2017)

        #zero income is ignored
        comp = RUSSIA.get_average_nominal_incomes([TYearIncome(2015, 0), TYearIncome(2016, 1500000), TYearIncome(2017, 2000000)])
        self.assertAlmostEqual(comp.declarant_income_growth, 33, places=3)  # 33% growth
        self.assertAlmostEqual(comp.population_income_growth, 3, places=3)  # 3% growth of 2017
        self.assertEqual(comp.min_year, 2016)
        self.assertEqual(comp.max_year, 2017)

        #incomes less than 12*MROT are ignored
        incomes = [TYearIncome(2012, 600), TYearIncome(2013, 189744), TYearIncome(2019, 407711)]
        comp = RUSSIA.get_average_nominal_incomes(incomes)
        self.assertAlmostEqual(comp.declarant_income_growth, 114, places=3)
        self.assertAlmostEqual(comp.population_income_growth, 37, places=3)
        self.assertEqual(comp.min_year, 2013)
        self.assertEqual(comp.max_year, 2019)

        #real example 1
        incomes = [TYearIncome(2012,1693027),TYearIncome(2013,2790949),TYearIncome(2017,4993935),TYearIncome(2019,6241840)]
        comp = RUSSIA.get_average_nominal_incomes(incomes)
        self.assertAlmostEqual(comp.declarant_income_growth, 268, places=3)
        self.assertAlmostEqual(comp.population_income_growth, 52   , places=3)
        self.assertEqual(comp.min_year, 2012)
        self.assertEqual(comp.max_year, 2019)

        #real example 2
        incomes = [TYearIncome(2012,783050),TYearIncome(2013,819684),TYearIncome(2014,692259),TYearIncome(2015,736241),TYearIncome(2016,780312),TYearIncome(2017,817646),TYearIncome(2018,817078),TYearIncome(2019,886266)]
        comp = RUSSIA.get_average_nominal_incomes(incomes)
        self.assertAlmostEqual(comp.declarant_income_growth, 13, places=3)
        self.assertAlmostEqual(comp.population_income_growth, 52, places=3)
        self.assertEqual(comp.min_year, 2012)
        self.assertEqual(comp.max_year, 2019)

        #real example 3
        incomes = [TYearIncome(2012,297096),TYearIncome(2013,856340),TYearIncome(2014,820063),TYearIncome(2015,730649),TYearIncome(2016,706835)]
        comp = RUSSIA.get_average_nominal_incomes(incomes)
        self.assertAlmostEqual(comp.declarant_income_growth, 137, places=3)
        self.assertAlmostEqual(comp.population_income_growth, 32, places=3)
        self.assertEqual(comp.min_year, 2012)
        self.assertEqual(comp.max_year, 2016)
