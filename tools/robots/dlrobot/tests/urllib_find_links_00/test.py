import os
from robots.common.find_link import find_links_in_html_by_text
from robots.common.robot_project import TRobotProject
from robots.common.web_site import  TProcessUrlTemporary, TUrlInfo
from robots.dlrobot.dlrobot import looks_like_a_declaration_link
from bs4 import BeautifulSoup
import urllib.parse
import logging

ROBOT_STEPS = [
    {
        'step_name': "declarations",
        'check_link_func': looks_like_a_declaration_link,
    }
]

if __name__ == "__main__":
    with TRobotProject(logging, "project.txt", ROBOT_STEPS, None) as project:
        project.read_project()
        office_info = project.offices[0]
        target = office_info.robot_steps[0]
        step_info = TProcessUrlTemporary(office_info, target, ROBOT_STEPS[0])
        start_page = "sved.html"
        html_path = os.path.join( os.path.dirname(os.path.realpath(__file__)), "html", start_page)
        soup = BeautifulSoup(open(html_path, encoding="utf8"), 'html.parser')
        some_sub_page = urllib.parse.urljoin(project.offices[0].morda_url, start_page)
        office_info.url_nodes[some_sub_page] = TUrlInfo(title="", step_name=None)
        find_links_in_html_by_text(step_info, some_sub_page, soup)
        url_info = office_info.url_nodes.get(some_sub_page)
        assert (url_info is not None)
        doc1 = urllib.parse.urljoin(project.offices[0].morda_url, 'doxod_2011.docx')
        child1 = url_info.linked_nodes.get(doc1)
        assert (child1 is not None)
        assert (len(child1['text']) > 0)

        doc2 = urllib.parse.urljoin(project.offices[0].morda_url, 'some_doc.docx')
        child2 = url_info.linked_nodes.get(doc2)
        assert (child2 is not None)
        assert (len(child2['text']) > 0)

        assert len(url_info.linked_nodes) == 2
        assert url_info.linked_nodes.get('http://pravo.gov.ru/proxy/ips/?docbody=&nd=102074279&rdk=&intelsearch') is None
