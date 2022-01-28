#read  https://rosstat.gov.ru/folder/11109/document/13259, таблица 11-01
from office_db.russian_regions import TRussianRegions
from declarations.region_data import TRossStatData, TRegionYearInfo


def main():
    regions = TRussianRegions()
    stat_data = TRossStatData()
    stat_data.load_from_disk()
    with open('/home/sokirko/tmp/rosstat_incomes/average_income.csv') as inp:
        for line in inp:
            cols = line.split("\t")
            found = False
            for stop_word in ['Среднедушевые', 'Рублей', '2016 год', 'I квартал', 'Российская Федерация', 'федеральный округ',
                              'в том числе', ' без ', 'Ямало-Ненецкий автономный округ', 'Предварительные', 'Начиная']:
                if line.find(stop_word) != -1:
                    found = True
                    break
            if found:
                continue
            region_str = cols[0].strip()
            region = regions.get_region_in_nominative(region_str)
            if region is None:
                raise Exception("cannot find region {}".format(region_str))
            assert len(cols) == 24
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