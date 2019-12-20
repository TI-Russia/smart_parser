import sys
from find_link import  click_first_link_and_get_url
from office_list import write_offices

def check_anticorr_link_text(text):
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
        if existing_link.get('url') != None and only_missing:
            continue


        sys.stderr.write(url + "\n")
        click_first_link_and_get_url(office_info, 'anticorruption_div', url,  check_anticorr_link_text, True)

        # manual fix list (sometimes they use images instead of text...)
        if url.find('fsin.su') != -1:
            office_info["anticorruption_div"] = {
                "url": "http://www.fsin.su/anticorrup2014/",
                "engine": "manual"
            }
        if url.find('fso.gov.ru') != -1:
            office_info["anticorruption_div"] = {
                "url": "http://www.fso.gov.ru/korrup.html",
                "engine": "manual"
            }

    write_offices(offices)
