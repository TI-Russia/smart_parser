
from office_db.region_data import TRossStatData
from rosstat import get_regions


def main():
    data = TRossStatData()
    data.load_from_disk()
    year = 2021
    with open("/home/sokirko/vybory2021.csv") as inp:
        for region, cols in get_regions(inp, False):
            assert len(cols) == 16
            info = data.get_or_create_data(region.id, 2021)
            info.er_election_2021 = float(cols[1].replace(',', '.'))

    data.save_to_disk(".new")


if __name__ == '__main__':
    main()