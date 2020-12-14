from django.apps import AppConfig
from source_doc_http.source_doc_client import TSourceDocClient
import sys


class DeclarationsConfig(AppConfig):
    name = 'declarations'
    SOURCE_DOC_CLIENT = None

    def ready(self):
        if 'runserver' in sys.argv:
            self.SOURCE_DOC_CLIENT = TSourceDocClient(TSourceDocClient.parse_args(['--timeout', '10']))
