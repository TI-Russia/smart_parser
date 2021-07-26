from .tomsk import tomsk_gov_ru
from .gossov_tatarstan_ru import gossov_tatarstan_ru


def process_adhoc(project):
    domain_name = project.web_site_snapshots[0].get_site_url()
    if domain_name == "tomsk.gov.ru":
        tomsk_gov_ru(project.web_site_snapshots[0])
        return True
    elif domain_name == "gossov.tatarstan.ru":
        gossov_tatarstan_ru(project.web_site_snapshots[0])
        return True
    return False
