from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from source_doc_http.source_doc_client import TSourceDocClient
from common.content_types import ACCEPTED_DOCUMENT_EXTENSIONS

import os


class TDeclarationSender:

    def __init__(self, logger, enable_smart_parser, enable_source_doc_server):
        self.logger = logger
        self.smart_parser_server_client = None
        if enable_smart_parser:
            sp_args = TSmartParserCacheClient.parse_args([])
            self.smart_parser_server_client = TSmartParserCacheClient(sp_args, logger)
        self.source_doc_client = None
        if enable_source_doc_server:
            sp_args = TSourceDocClient.parse_args([])
            self.source_doc_client = TSourceDocClient(sp_args, logger)

    def send_declaraion_files_to_other_servers(self, dlrobot_project_folder):
        doc_folder = os.path.join(dlrobot_project_folder, "result")
        if os.path.exists(doc_folder):
            for website in os.listdir(doc_folder):
                website_folder = os.path.join(doc_folder, website)
                for doc in os.listdir(website_folder):
                    _, extension = os.path.splitext(doc)
                    if extension in ACCEPTED_DOCUMENT_EXTENSIONS:
                        file_path = os.path.join(website_folder, doc)
                        if self.smart_parser_server_client is not None:
                            self.logger.debug("send {} to smart_parser_server".format(doc))
                            self.smart_parser_server_client.send_file(file_path)
                        if self.source_doc_client is not None:
                            self.logger.debug("send {} to source_doc_server".format(doc))
                            self.source_doc_client.send_file(file_path)
