import os
import json
import re
from unidecode import unidecode

BRAND_FILE_PATH = os.path.join(os.path.dirname(__file__), "../data/car_brands.json")
IMAGE_FILE_PATH = os.path.join(os.path.dirname(__file__), "../disclosures/static/images/carbrands")


class CarBrands:
    def __init__(self, *args, **kwargs):
        self.brand_first_words = dict()
        self.word_rgx = re.compile("([\w-]+)")
        self.brand_dict = dict()
        self.build_first_words()

    def build_first_words(self):
        with open (BRAND_FILE_PATH) as inp:
            self.brand_dict = json.load(inp)
        for brand_id, brand_info in self.brand_dict.items():
            for s in brand_info['synonyms']:
                words = s.lower().split(' ')
                if words[0] in self.brand_first_words:
                    print ("{} is ambiguous".format(words[0]))
                    assert (words[0] not in self.brand_first_words)
                self.brand_first_words[words[0]] = brand_id

    def get_brand_info(self, brand_id):
        return self.brand_dict[brand_id]

    def get_brand_name(self, brand_id):
        return self.brand_dict[brand_id]['name']

    def find_brands(self, s):
        brands = list()
        for w in self.word_rgx.findall(s.lower()):
            brand = self.brand_first_words.get(w)
            if brand is None:
                hyphen = w.find('-')
                if hyphen != -1:
                    brand = self.brand_first_words.get(w[:hyphen])
            if brand is None:
                brand = self.brand_first_words.get(unidecode(w))

            if brand is not None:
                brands.append (brand)
        return brands

    def get_image_url(self, brand_id):
        return os.path.join("/static/images/carbrands", self.get_brand_info(brand_id)['img'])


CAR_BRANDS = CarBrands()