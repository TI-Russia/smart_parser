import socket
import os
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

if socket.gethostname() == "dell-7440":
    DEBUG = True

ALLOWED_HOSTS = ['disclosures.ru', '95.165.96.61', 'localhost', '192.168.100.151', '192.168.100.206', '185.237.97.32',
                 '192.168.8.103', '127.0.0.1']

ELASTICSEARCH_INDEX_NAMES = {
    'section_index_name': 'declaration_sections_prod',
    'person_index_name': 'declaration_person_prod',
    'office_index_name': 'declaration_office_prod',
    'file_index_name': 'declaration_file_prod',
}

os.environ['DISCLOSURES_DATABASE_NAME'] = os.environ.get('DISCLOSURES_DATABASE_NAME', 'disclosures_db')

os.environ['SOURCE_DOC_SERVER_ADDRESS'] = os.environ.get('SOURCE_DOC_SERVER_ADDRESS', '192.168.100.151:8090')

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SAMESITE = 'None'

from .common import *