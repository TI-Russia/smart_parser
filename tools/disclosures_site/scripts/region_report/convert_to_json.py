# adhoc script, delete it in 2023
import json
from office_db.russian_regions import TRussianRegions
import os


def read_russia_duck_consulting_csv(basename, year_to_read):
    regions = TRussianRegions()
    filepath = os.path.join(os.path.dirname(__file__), "../../data/", basename)
    incomes_all_citizen = dict()
    with open(filepath, "r") as inp:
        for line in inp:
            year, region_str, income = line.split(',')
            region = regions.get_region_in_nominative(region_str)
            assert region is not None
            year = int(year)
            if year != year_to_read:
                continue
            income = income.strip('\n')
            if len(income) > 0:
                incomes_all_citizen[region.id] = int(float(income))
    return incomes_all_citizen


def main():
    stat = dict()
    regions = TRussianRegions()
    for year in range(2011, 2020):
        incomes_all_citizen = read_russia_duck_consulting_csv("median_income.csv", year)
        for region_id, v in incomes_all_citizen.items():
            if region_id not in stat:
                stat[region_id] = dict()
            stat[region_id][year] = dict()
            stat[region_id][year]['median_income'] = v

        population = read_russia_duck_consulting_csv("russia_population.csv", year)
        for region_id, v in population.items():
            if region_id not in stat:
                stat[region_id] = dict()
            if year not in stat[region_id]:
                stat[region_id][year] = dict()
            stat[region_id][year]['population'] = v
        for r in regions.iterate_regions():
            if TRussianRegions.regions_was_captured_in_2014(r.id) and year <= 2014:
                continue
            if r.id == 111:
                continue
            v = stat[r.id][year]
            assert 'population'  in v
    with open(os.path.join(os.path.dirname(__file__), "../../data/ross_stat.json"), "w") as outp:
        json.dump(stat, outp, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()