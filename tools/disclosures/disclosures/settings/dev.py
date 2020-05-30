import os
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost']

os.environ['DISCLOSURES_DB_HOST'] = 'localhost'

from .common import *