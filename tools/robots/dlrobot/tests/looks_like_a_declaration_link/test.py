import os
from robots.common.find_link import find_links_in_html_by_text
from robots.common.robot_project import TRobotProject
from robots.common.robot_step import TRobotStep, TUrlInfo
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

def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_logger")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def check_has_child(office_info, parent, child):
    url_info = office_info.url_nodes.get(parent)
    assert (url_info is not None)
    child_url = urllib.parse.urljoin(office_info.morda_url, child)
    child_info = url_info.linked_nodes.get(child_url)
    assert (child_info is not None)
    assert (len(child_info['text']) > 0)


if __name__ == "__main__":
    logger = setup_logging("dlrobot.log")
    with TRobotProject(logger, "project.txt", ROBOT_STEPS, "result") as project:
        project.read_project()
        office_info = project.offices[0]
        office_info.create_export_folder()
        target = office_info.robot_steps[0]
        step_info = TRobotStep(office_info, ROBOT_STEPS[0])
        start_page = "sved.html"
        html_path = os.path.join( os.path.dirname(os.path.realpath(__file__)), "html", start_page)
        soup = BeautifulSoup(open(html_path, encoding="utf8"), 'html.parser')
        some_sub_page = urllib.parse.urljoin(project.offices[0].morda_url, start_page)
        office_info.url_nodes[some_sub_page] = TUrlInfo(title="", step_name=None)
        find_links_in_html_by_text(step_info, some_sub_page, soup)

        check_has_child(office_info, some_sub_page, 'doxod_2011.docx')
        check_has_child(office_info, some_sub_page, 'some_doc.docx')
        check_has_child(office_info, some_sub_page, 'broken.doc')
