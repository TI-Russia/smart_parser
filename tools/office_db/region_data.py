from office_db.russian_regions import TRussianRegions

import json
import os


# TRegionYearInfo.population
# 1. Население по регионам строится конструктором от Росстата,
# https://showdata.gks.ru/report/278928/?&filter_1_0=2019-01-01+00%3A00%3A00%7C-56%2C2020-01-01+00%3A00%3A00%7C-56%2C2021-01-01+00%3A00%3A00%7C-56&filter_2_0=127937&filter_3_0=13035%2C13441%2C13087%2C13091%2C13096%2C13109%2C13120%2C13148%2C13169%2C13180%2C13193%2C13202%2C13253%2C13281%2C13305%2C13310%2C13142%2C13319%2C13356%2C13200%2C13442%2C13388%2C13392%2C13078%2C13079%2C109349%2C13105%2C13137%2C13185%2C13229%2C13233%2C13268%2C13183%2C13443%2C108674%2C320258%2C13359%2C13384%2C108675%2C13041%2C13085%2C13101%2C13272%2C108676%2C108671%2C13373%2C13133%2C13379%2C13404%2C13402%2C13425%2C13062%2C13444%2C13361%2C13396%2C13399%2C13407%2C13416%2C13428%2C13260%2C109208%2C13166%2C13112%2C13248%2C13256%2C13172%2C13286%2C13338%2C13445%2C13177%2C13297%2C13323%2C13324%2C13329%2C109350%2C13341%2C13446%2C320380%2C13382%2C13413%2C13422%2C13036%2C109269%2C13048%2C109340%2C109342%2C13123%2C320402%2C109118%2C13238%2C13242%2C13313%2C13447%2C320381%2C13368%2C13348%2C13432%2C13153%2C109140%2C13056%2C13069%2C13073%2C13196%2C13292%2C13439%2C13353%2C108677&filter_4_0=170792%2C173935%2C155852%2C173936%2C155854%2C155855%2C155857%2C204599%2C155858%2C155859%2C155860%2C155861%2C155863%2C155864%2C155865%2C204601%2C204602%2C155866%2C155867%2C155868%2C155869%2C204603%2C155870%2C204604%2C155871%2C155872%2C155873%2C155874%2C155875%2C155876%2C155877%2C155878%2C155879%2C155880%2C155881%2C155882%2C155883%2C204607%2C155884%2C204609%2C204610%2C211936%2C204611%2C204612%2C155886%2C155887%2C155888%2C155889%2C155890%2C155891%2C155892%2C155893%2C155894%2C155895%2C155896%2C155897%2C155898%2C155899%2C155900%2C155901%2C155902%2C155903%2C211937%2C209086%2C173937%2C155904%2C170794%2C155905%2C155906%2C155907%2C155908%2C204616%2C155909%2C204617%2C155910%2C155911%2C155912%2C155913%2C155914%2C155915%2C155916%2C155917%2C155918%2C155919%2C155920%2C155921%2C155922%2C155923%2C155924%2C155925%2C155926%2C204620%2C155927%2C155928%2C204621%2C155929%2C155930%2C155931%2C155932%2C155933%2C155934%2C155935%2C204623%2C155936%2C155937%2C204624%2C155938%2C155939%2C155940%2C155941%2C155942%2C155943%2C155944%2C155945%2C155946%2C155947%2C155948%2C155949%2C155950%2C155951%2C155952%2C155953%2C155954%2C155955%2C155956%2C155957%2C204628%2C204629%2C155958%2C204630%2C155959%2C204631%2C204632%2C204633%2C204634%2C204635%2C155960%2C155961%2C155962%2C155963%2C204637%2C155964%2C155965%2C155966%2C155967%2C155968%2C155969%2C155970%2C155971%2C155972%2C155973%2C155974%2C204639%2C155975&rp_submit=t
# выгружается в виде csv  и парсится скриптом disclosures_site/scripts/rosstat/population.py

# TRegionYearInfo.median_salary2 и TRegionYearInfo.average_salary2
# 2. Медианная зарплата до 2019 года взята с сайта https://russia.duck.consulting/maps/105/2019, туда она попала
# из Росстата (https://rosstat.gov.ru/compendium/document/13268 , "Сведения о распределении численности работников по размерам заработной платы" (31 или 32 таблица)  )
#  Росстат проводит раз в два года исследования на 100000 предприятиях = 27 млн. человек по зарплате.
# Эта зарплата не усредняется по году, берется только за апрель.
#  Поскольку раз в два года, я добавил двойку к названию: median_salary2  и average_salary2.
#  В 2021 году я увидел, russia.duck.consulting тормозит # и не распарсил данные от Росстата, пришлось лезть на Росстат.
# Скрипт находится здесь  tools/disclosures_site/scripts/rosstat/salary.py)


#3. TRegionYearInfo.average_income
# Среднедушевой доход берется от Росстата https://rosstat.gov.ru/folder/11109/document/13259 ,  таблица 11-01
#  будем усреднять его по всем кварталам.

#4. TRegionYearInfo.average_salary
#https://rosstat.gov.ru/labor_market_employment_salaries
#"Информация о среднемесячной начисленной заработной плате наемных работников в организациях, у индивидуальных предпринимателей и физических лиц (среднемесячном доходе от трудовой деятельности)"
#Среднемесячная номинальная начисленная заработная плата работников по полному кругу организаций в целом по экономике по субъектам Российской Федерации с 2018 года , рублей
# Это информация о генеральной совокупности, но пока я ее не использую нигде, поэтому эта информация не загружена в файл.

#5.  TRegionYearInfo.er_election_2021
# Голосование за ЕР в 2021 году ru.wikipedia.org/wiki/Выборы_в_Государственную_думу_(2021)

class TRegionYearInfo:
    def __init__(self, population=None, median_salary2=None, average_income=None, average_salary2=None,
                 average_salary=None, er_election_2021=None):
        self.population = population
        self.median_salary2 = median_salary2
        self.average_salary2 = average_salary2
        self.average_income = average_income
        self.average_salary = average_salary
        self.er_election_2021 = er_election_2021

    @staticmethod
    def from_json(j):
        r = TRegionYearInfo()
        r.population = j.get('population')
        r.median_salary2 = j.get('median_salary2')
        r.average_salary2 = j.get('average_salary2')
        r.average_income = j.get('average_income')
        r.average_salary = j.get('average_salary')
        r.er_election_2021 = j.get('er_election_2021')
        r.check()
        return r

    def check(self):
        if self.median_salary2 is not None:
            assert self.median_salary2 > 5000
            assert self.median_salary2 < 300000
        if self.population is not None:
            assert self.population > 10000
        if self.average_income is not None:
            assert self.average_income > 10000

        #Медианная зарплата составляет около 70 % от средней.
        #https://ru.wikipedia.org/wiki/%D0%94%D0%BE%D1%85%D0%BE%D0%B4%D1%8B_%D0%BD%D0%B0%D1%81%D0%B5%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F_%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D0%B8?fbclid=IwAR1PahTMesEzJmTJ9IRShaxUKNWfnGuqjLO8KeLS3yKjH6qo0EKlRHGgcjU
        if self.median_salary2 is not None and self.average_salary2 is not None:
            assert self.median_salary2 < self.average_salary2

        #incomes are calculated for all people (children and older people)
        if self.average_salary2 is not None and self.average_income is not None:
            assert self.average_salary2 > self.average_income

    def to_json(self):
        r = dict()
        if self.population is not None:
            r['population'] = self.population
        if self.median_salary2 is not None:
            r['median_salary2'] = self.median_salary2
        if self.average_salary2 is not None:
            r['average_salary2'] = self.average_salary2
        if self.average_income is not None:
            r['average_income'] = self.average_income
        if self.average_salary is not None:
            r['average_salary'] = self.average_salary
        if self.er_election_2021 is not None:
            r['er_election_2021'] = self.er_election_2021
        return r


class TRossStatData:
    def __init__(self, regions=None):
        self.region_stat = dict()
        self.regions = regions
        if self.regions is None:
            self.regions = TRussianRegions()
        self.file_path = os.path.join(os.path.dirname(__file__), "data/ross_stat.json")

    def load_from_disk(self):
        with open(self.file_path) as inp:
            for key, years in json.load(inp).items():
                region = self.regions.get_region_by_id(int(key))
                assert region is not None
                region_id = region.id
                if region_id not in self.region_stat:
                    self.region_stat[region_id] = dict()
                for year, stat in years.items():
                    self.region_stat[int(region_id)][int(year)] = TRegionYearInfo.from_json(stat)

    def save_to_disk(self, postfix=""):
        d = dict()
        with open(self.file_path + postfix, "w") as outp:
            for region_id, years in self.region_stat.items():
                d[region_id] = dict()
                for year, info in years.items():
                    d[region_id][year] = info.to_json()
            json.dump(d, outp, indent=3, ensure_ascii=False)

    def check(self, year: int):
        for r in self.regions.iterate_regions():
            if r.id not in self.region_stat:
                raise Exception("region {}, region_id={} is missing".format(r.name, r.id))
            if year not in self.region_stat[r.id]:
                raise Exception("year {} region {}, region_id={} is missing".format(year, r.name, r.id))

    def get_data(self, region_id, year: int) -> TRegionYearInfo:
        return self.region_stat.get(region_id, dict()).get(year)

    def get_or_create_data(self, region_id, year: int) -> TRegionYearInfo:
        return self.region_stat.get(region_id, dict()).get(year, TRegionYearInfo())

    def set_data(self, region_id, year: int, info: TRegionYearInfo):
        info.check()
        r = self.region_stat.get(region_id)
        assert r is not None
        r[year] = info

    def get_or_predict_median_salary(self, region_id: int, year: int) -> int:
        d = self.get_data(region_id, year)
        if d is not None and d.median_salary2 is not None:
            return d.median_salary2
        d1 = self.get_data(region_id, year - 1)
        d2 = self.get_data(region_id, year + 1)
        if d1 is not None and d1.median_salary2 is not None and d2 is not None and d2.median_salary2 is not None:
            return int((d1.median_salary2 + d2.median_salary2)/2)
        return None