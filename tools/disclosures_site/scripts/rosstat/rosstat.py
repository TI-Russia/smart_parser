from office_db.russian_regions import TRussianRegions
from common.primitives import normalize_whitespace


def get_regions(inp, start_after_rf_line=True):
    regions = TRussianRegions()
    start = not start_after_rf_line
    used_regions = set()
    for line in inp:
        if not start:
            if line.find("Российская Федерация") != -1:
                start = True
            continue
        found_stop_word = False
        for stop_word in ['среднедушевые', 'рублей', '2016 год', 'i квартал', 'российская федерация',
                          'федеральный округ', 'наименование',
                          'в том числе', ' без ', '(кроме ', 'ямало-ненецкий автономный округ', 'предварительные', 'начиная']:
            if line.lower().find(stop_word) != -1:
                found_stop_word = True
                break
        if found_stop_word:
            continue
        cols = line.split("\t")
        region_str = cols[0].strip().replace('H', 'Н')
        region_str = normalize_whitespace(region_str)
        region = regions.get_region_in_nominative(region_str)
        if region is None:
            raise Exception("cannot find region {}".format(region_str))
        used_regions.add(region.id)
        yield region, cols[1:]
    for r in regions.iterate_inner_regions_without_joined():
        if r.id not in used_regions:
            raise Exception("region {}, id={} is not found in the input file".format(r.name, r.id))
