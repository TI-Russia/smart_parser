import os
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost']

os.environ['DISCLOSURES_DB_HOST'] = 'localhost'

ELASTICSEARCH_INDEX_NAMES = {
    'section_index_name': 'declaration_sections_dev',
    'person_index_name': 'declaration_person_dev',
}

from .common import *
