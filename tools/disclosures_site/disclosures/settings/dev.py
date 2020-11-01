import os
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost']

#   os.environ['DISCLOSURES_DB_HOST'] = 'localhost'

ELASTICSEARCH_INDEX_NAMES = {
    'section_index_name': 'declaration_sections_dev',
    'person_index_name': 'declaration_person_dev',
    'office_index_name': 'declaration_office_dev',
    'file_index_name': 'declaration_file_dev',
}

os.environ['DISCLOSURES_DATABASE_NAME'] = 'disclosures_db_dev'


from .common import *
