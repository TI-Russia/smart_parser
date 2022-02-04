#read  https://rosstat.gov.ru/folder/11109/document/13259, таблица 11-01
from office_db.region_data import TRossStatData, TRegionYearInfo
from rosstat import get_regions


def main():
    stat_data = TRossStatData()
    stat_data.load_from_disk()
    with open('/home/sokirko/tmp/rosstat_incomes/average_income.csv') as inp:
        for region, cols in get_regions(inp)
            year = 2016
            for i in range(1, len(cols), 4):
                data = list()
                for k in range(i,i+4):
                    if k < len(cols) and len(cols[k].strip()) > 0:
                        v = cols[k].strip()
                        if not v.isdigit():
                            raise Exception("not a number {}".format(v))
                        data.append(int(v))
                if len(data) > 0:
                    d = stat_data.get_data(region.id, year)
                    if d is None:
                        d = TRegionYearInfo()
                    d.average_income = int(sum(data)/len(data))
                    stat_data.set_data(region.id, year, d)
                year += 1
        stat_data.save_to_disk(".new")


if __name__ == '__main__':
    main()