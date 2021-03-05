from bs4 import BeautifulSoup
import sys
import json


def include_fns_json_to_html(json_path, html_path):
    assert json_path.endswith('json')
    assert html_path.endswith('html')
    with open(json_path) as inp:
        filters = json.load(inp)['filters']

    if 'insp_name' in filters:
        department = filters['insp_name']
    else:
        department = filters.get('upr_name', '')

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

    with open(html_path, "w") as outp:
        outp.write(str(soup))


if __name__ == "__main__":
    include_fns_json_to_html(sys.argv[1], sys.argv[2])
