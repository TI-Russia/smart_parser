from django.apps import AppConfig
from source_doc_http.source_doc_client import TSourceDocClient
import sys
import telegram_send
import platform


class DeclarationsConfig(AppConfig):
    name = 'declarations'
    SOURCE_DOC_CLIENT = None

    def ready(self):
        if 'runserver' in sys.argv or  sys.argv[0].endswith('gunicorn'):
            try:
                c = TSourceDocClient(TSourceDocClient.parse_args(['--timeout', '10']))
                DeclarationsConfig.SOURCE_DOC_CLIENT = c
            except Exception as exp:
                try:
                    telegram_send.send(messages=["request failed to source doc server from hostname={}".format(platform.node())])
                except Exception as exp:
                    pass

