class TYearIncome:
    def __init__(self, year, income):
        self.year = year
        self.income = income

    def __str__(self):
        return "TYearIncome({},{})".format(self.year, self.income)

    @staticmethod
    def get_income_diff(income1, income2):
        return int(100.0 * (float(income2) - float(income1)) / float(income1))
