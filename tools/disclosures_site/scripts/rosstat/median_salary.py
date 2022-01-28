# парсим 31 таблица из "Сведения о распределении численности работников по размерам заработной платы" от Росстата

from disclosures_site.declarations.rosstat_data import TRossStatData, TRegionYearInfo
from common.primitives import normalize_whitespace


def main():
    data = TRossStatData()
    data.load_from_disk()
    year = 2021
    with open("/home/sokirko/Tab_31.csv") as inp:
        for line in inp:
            name, value = line.strip().split('\t')
            value = int(value)
            name = normalize_whitespace(name)
            name = name.replace('H', 'Н')
            region = data.regions.get_region_in_nominative(name)
            if region is None:
                raise Exception("region {} is not found".format(name))
            if year not in data.region_stat[region.id]:
                data.region_stat[region.id][year] = TRegionYearInfo(population=None, median_salary=value)
            else:
                data.region_stat[region.id][year].median_salary = value
    data.save_to_disk(".new")


if __name__ == '__main__':
    main()