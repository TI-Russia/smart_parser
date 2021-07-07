from common.download import TDownloadedFile
from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from common.html_parser import THtmlParser
from common.link_info import TLinkInfo, TClickEngine


def gossov_tatarstan_ru(web_site: TWebSiteCrawlSnapshot):
    web_site.create_export_folder()
    robot_step = web_site.robot_steps[-1]
    driver = robot_step.get_selenium_driver()
    elements = driver.navigate_and_get_links("https://gossov.tatarstan.ru/structure/deputaty")
    for element in elements:
        person_href = element.get_attribute('href')
        if person_href is not None and person_href.find('person_id') != -1:
            robot_step.add_link_wrapper(TLinkInfo(TClickEngine.manual, robot_step.website.main_page_url, person_href))
            file = TDownloadedFile(person_href)
            parser = THtmlParser(file.data, url=person_href)
            for html_link in THtmlParser(file.data, url=person_href).soup.findAll("a"):
                href_pdf = html_link.attrs.get('href', '')
                if href_pdf.find('revenue') != -1:
                    href_pdf = parser.make_link_soup(href_pdf)
                    robot_step.add_link_wrapper (TLinkInfo(TClickEngine.manual, person_href, href_pdf))
                    