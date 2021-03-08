from bs4 import BeautifulSoup
import os
import json

if __name__ == "__main__":
    car_brand_path = "../disclosures/static/carbrand"
    if not os.path.exists(car_brand_path):
        os.mkdir(car_brand_path)

    car_brands = list()
    with open ("kuruh_ru_emblem.html", "rb") as inp:
        html_data = inp.read()
        soup = BeautifulSoup(html_data, 'html.parser')
        for table in soup.findAll('table')[3:]:
            for tr in table.findAll('tr'):
                for td in tr.findAll('td'):
                    for img in td.findAll('img'):
                        if 'src' in img.attrs:
                            basen = os.path.basename(img.attrs['src'])
                            filename,_ = os.path.splitext(basen)
                            car_brand = {
                                'name': img.attrs['alt'],
                                'img':  basen,
                                "synonyms": [filename, img.attrs['alt'].lower()]
                            }
                            car_brands.append(car_brand)
                            my_file =  os.path.join(car_brand_path, "images", basen)
                            if not os.path.exists(my_file):
                                print ("cannot find jpg {}".format(my_file))

    with open(os.path.join(car_brand_path, "car_brands.json"), "w") as outp:
        json.dump(car_brands, outp, indent=4, ensure_ascii=False)

