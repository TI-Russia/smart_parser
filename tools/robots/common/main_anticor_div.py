import sys
from find_link import  get_links
from office_list import write_offices

def check_anticorr_link_text(text, href=None):
    text = text.strip().lower()
    if text.startswith(u'противодействие'):
        return text.find("коррупц") != -1
    return False

def find_anticorruption_div(offices, only_missing=False):
    for office_info in offices:
        url = office_info['url']

        existing_link = office_info.get('anticorruption_div', {})
        if existing_link.get('engine', '') == 'manual':
            sys.stderr.write("skip manual url updating " + url + "\n")
            continue
        if len(existing_link.get('links', [])) > 0 and only_missing:
            continue


        sys.stderr.write(url + "\n")
        get_links(office_info, 'anticorruption_div', url,  check_anticorr_link_text)

        # manual fix list (sometimes they use images instead of text...)
        if url.find('fsin.su') != -1:
            office_info["anticorruption_div"] = [{
                "url": "http://www.fsin.su/anticorrup2014/",
                "engine": "manual"
            }]

        if url.find('fso.gov.ru') != -1:
            office_info["anticorruption_div"] = [{
                "url": "http://www.fso.gov.ru/korrup.html",
                "engine": "manual"
            }]

    write_offices(offices)
