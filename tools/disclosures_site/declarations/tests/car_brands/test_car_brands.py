from django.test import TestCase
from declarations.car_brands import CarBrands
import json
import os


class ResolveCarBrands(TestCase):

    def test_primitive_car_brand(self):
        def check(str, canon_brands):
            brands = list(brand_finder.get_brand_name(x) for x in brand_finder.find_brands(str))
            self.assertListEqual(brands, canon_brands)

        brand_finder = CarBrands()
        check("Рено альфа ромео", ["Renault", "Alfa Romeo"])
        check("КIА", ["KIA"]) #unidecode
        check("ВАЗ Lada \n217030", ["Lada"])
        check("ВАЗ Lada \n217030", ["Lada"])
        check("л/а ВАЗ 2190 Гранта", ["Lada"])
        check("легковой автомобиль ВАЗ-2190 Лада Гранта", ["Lada"])
        check("легковой автомобиль: \nМАЗДА Мазда-6", ["Mazda"])
        check("Легковой автомобиль Пежо Peugeot", ["Peugeot"])
        check("автомобиль Мерседес-\nБенц GL \n350 CDI	Mersedes-Benz", ["Mersedes-Benz"])

    def test_car_brand_1000(self):
        brand_finder = CarBrands()
        with open(os.path.join(os.path.dirname(__file__), 'cases_1000.txt')) as inp:
            for test_case in json.load(inp):
                for k, canon_brands in test_case.items():
                    brands = list(brand_finder.get_brand_name(x) for x in brand_finder.find_brands(k))
                    self.assertListEqual(canon_brands, brands)

