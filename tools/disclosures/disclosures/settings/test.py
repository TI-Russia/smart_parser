import os
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost']

os.environ['DISCLOSURES_DB_HOST'] = 'localhost'

ELASTICSEARCH_INDEX_NAMES = {
    'section_index_name': 'declaration_sections_test',
    'person_index_name': 'declaration_person_test',
    'office_index_name': 'declaration_office_test',
    'office_index_name': 'declaration_office_prod',

}

from .common import *

