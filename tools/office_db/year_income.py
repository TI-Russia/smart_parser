class TYearIncome:
    def __init__(self, year: int, income: int):
        assert 1989 < year < 2050
        self.year = year
        self.income = income

    def __str__(self):
        return "TYearIncome({},{})".format(self.year, self.income)

    def __lt__(self, other):
        if self.year != other.year:
            return self.year < other.year
        return self.income < other.income

    # Russian: темп прироста
    @staticmethod
    def get_growth_rate(income1, income2):
        return int(100.0 * (float(income2) - float(income1)) / float(income1))
