from bs4 import BeautifulSoup
import json
import sys
import os
from common.russian_regions import TRussianRegions


def include_fns_json_to_html(json_path, html_path):
    regions = TRussianRegions()
    assert json_path.endswith('json')
    assert html_path.endswith('html')
    with open(json_path) as inp:
        filters = json.load(inp)['filters']

    upr_name = filters.get('upr_name', '')
    if upr_name is None:
        upr_name = ''
    if 'insp_name' in filters:
        department = filters['insp_name']
    else:
        department = upr_name
    if department is None:
        department = ''

    url = "service.nalog.ru"
    if len(upr_name) > 1 and upr_name[0:4].endswith("00"):
        region = regions.get_region_in_nominative_and_dative(upr_name)
        assert region is not None
        url = "{}.{}".format(region.id, url)

    if filters.get('otdel_name') is not None:
        if len(department) > 0:
            department += '; '
        department += filters.get('otdel_name')

    with open(html_path, "rb") as inp:
        file_data = inp.read().strip()
        if file_data.endswith(b'<html>'):
            file_data = file_data[:-len('<html>')] + b'</html>'
        soup = BeautifulSoup(file_data, "html.parser")

    metatag = soup.new_tag('meta')
    metatag.attrs['name'] = 'smartparser_department'
    metatag.attrs['content'] = department
    soup.html.insert(2, metatag)

    metatag = soup.new_tag('meta')
    metatag.attrs['name'] = 'smartparser_url'
    metatag.attrs['content'] = url
    soup.html.insert(2, metatag)

    with open(html_path, "w") as outp:
        outp.write(str(soup))


if __name__ == "__main__":
    html_path = sys.argv[1]
    json_path = os.path.splitext(html_path)[0] + ".json"
    if os.path.exists(json_path):
        include_fns_json_to_html(json_path, html_path)
