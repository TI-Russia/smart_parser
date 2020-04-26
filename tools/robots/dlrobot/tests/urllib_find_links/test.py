import sys
from robots.common.find_link import find_links_in_html_by_text
from robots.common.office_list import TRobotProject, TProcessUrlTemporary, TUrlInfo
from robots.dlrobot.dlrobot import looks_like_a_declaration_link
from bs4 import BeautifulSoup

ROBOT_STEPS = [
    {
        'step_name': "declarations",
        'check_link_func': looks_like_a_declaration_link,
    }
]

if __name__ == "__main__":
    with TRobotProject("arshush.ru.txt", ROBOT_STEPS) as project:
        project.read_project()
        office_info = project.offices[0]
        target = office_info.robot_steps[0]
        step_info = TProcessUrlTemporary(office_info, target, ROBOT_STEPS[0])
        soup = BeautifulSoup(open("www.arshush.ru.html", encoding="utf8"), 'html.parser')
        some_sub_page = "http://arshush.ru/income"
        office_info.url_nodes[some_sub_page] = TUrlInfo(title="",step_name=None)
        find_links_in_html_by_text(step_info, some_sub_page, soup)
        url_info = office_info.url_nodes.get(some_sub_page)
        assert (url_info is not None)
        child1 = url_info.linked_nodes.get('http://arshush.ru/downloads/2011/doxod_1.docx')
        assert (child1 is not None)
        assert (len(child1['text']) > 0)

        child2 = url_info.linked_nodes.get('http://arshush.ru/downloads/2011/some_doc.docx')
        assert (child2 is not None)
        assert (len(child2['text']) > 0)
