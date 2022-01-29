# парсим Tab_31 из "Сведения о распределении численности работников по размерам заработной платы" от Росстата

from disclosures_site.declarations.region_data import TRossStatData
from rosstat import get_regions


def main():
    data = TRossStatData()
    data.load_from_disk()
    year = 2021
    with open("/home/sokirko/tmp/rosstat/zarplata2021/Tab_31.csv") as inp:
        for region, cols in get_regions(inp):
            assert len(cols) == 3
            info = data.get_or_create_data(region.id, year)
            info.median_salary = int(cols[0])
            info.average_salary = int(cols[1])
            data.set_data(region.id, year, info)

    data.save_to_disk(".new")


if __name__ == '__main__':
    main()