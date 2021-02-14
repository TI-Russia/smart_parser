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

    def test_car_brand_1000(self):
        brand_finder = CarBrands()
        with open(os.path.join(os.path.dirname(__file__), 'cases_1000.txt')) as inp:
            for test_case in json.load(inp):
                for k, canon_brands in test_case.items():
                    brands = list(brand_finder.get_brand_name(x) for x in brand_finder.find_brands(k))
                    self.assertListEqual(brands, canon_brands)

