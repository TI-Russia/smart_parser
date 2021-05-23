import os
import sys
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '192.168.100.26']

#   os.environ['DISCLOSURES_DB_HOST'] = 'localhost'

if len(sys.argv) > 0 and sys.argv[1] == "test":
    postfix_elastic_search_index = "test"
else:
    postfix_elastic_search_index = "dev"

ELASTICSEARCH_INDEX_NAMES = {
    'section_index_name': 'declaration_sections_' + postfix_elastic_search_index,
    'person_index_name': 'declaration_person_' + postfix_elastic_search_index,
    'office_index_name': 'declaration_office_' + postfix_elastic_search_index,
    'file_index_name': 'declaration_file_' + postfix_elastic_search_index,
}


os.environ['DISCLOSURES_DATABASE_NAME'] = os.environ.get('DISCLOSURES_DATABASE_NAME', 'disclosures_db_dev')


from .common import *
