from django.test import TestCase
from declarations.nominal_income import get_average_nominal_incomes, YearIncome


class NominalIncome(TestCase):

    def test_nominal_income(self):
        # out of year scope
        self.assertIsNone(get_average_nominal_incomes([YearIncome(2008, 1), YearIncome(2009, 2)]))

        # one year is not enough
        self.assertIsNone(get_average_nominal_incomes([YearIncome(2015,1)]))

        # two years
        comp = get_average_nominal_incomes([YearIncome(2015, 100), YearIncome(2016, 200)])
        self.assertEqual(comp.declarant_income, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income, 1)  # 1.5% growth
        self.assertEqual(comp.min_year, 2016)
        self.assertEqual(comp.max_year, 2016)

        # 3 years
        comp = get_average_nominal_incomes([YearIncome(2015, 100), YearIncome(2016, 150), YearIncome(2017, 200)])
        self.assertEqual(comp.declarant_income, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income, 4, places=3)  # 4.5% growth
        self.assertEqual(comp.min_year, 2016)
        self.assertEqual(comp.max_year, 2017)

        #2040  year is ignored
        comp = get_average_nominal_incomes([YearIncome(2015, 100), YearIncome(2016, 150), YearIncome(2017, 200),
                                            YearIncome(2040, 3000)])
        self.assertEqual(comp.declarant_income, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income, 4, places=3)  # 4.5% growth
        self.assertEqual(comp.min_year, 2016)
        self.assertEqual(comp.max_year, 2017)

        #2000  year is ignored
        comp = get_average_nominal_incomes([YearIncome(2000, 1), YearIncome(2015, 100),
                                            YearIncome(2016, 150), YearIncome(2017, 200)])
        self.assertEqual(comp.declarant_income, 100) # 100% growth
        self.assertAlmostEqual(comp.population_income, 4, places=3)  # 4.5% growth
        self.assertEqual(comp.min_year, 2016)
        self.assertEqual(comp.max_year, 2017)

        #zero income is ignored
        comp = get_average_nominal_incomes([YearIncome(2015, 0), YearIncome(2016, 150), YearIncome(2017, 200)])
        self.assertAlmostEqual(comp.declarant_income, 33, places=3)  # 33% growth
        self.assertAlmostEqual(comp.population_income, 2, places=3)  # 3% growth of 2017
        self.assertEqual(comp.min_year, 2017)
        self.assertEqual(comp.max_year, 2017)
