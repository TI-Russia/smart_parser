# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['disclosures.ru', '95.165.96.61']

ELASTICSEARCH_INDEX_NAMES = {
    'section_index_name': 'declaration_sections_prod',
    'person_index_name': 'declaration_person_prod',
    'office_index_name': 'declaration_office_prod',
    'file_index_name': 'declaration_file_prod',
}

from .common import *