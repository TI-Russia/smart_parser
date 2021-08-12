from declarations.input_json import TSourceDocument, TDeclaratorReference,  TDlrobotHumanFile, TIntersectionStatus
from common.archives import TDearchiver
from source_doc_http.source_doc_client import TSourceDocClient
from ConvStorage.conversion_client import TDocConversionClient
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from common.logging_wrapper import setup_logging
from common.primitives import build_dislosures_sha256
from common.urllib_parse_pro import urlsplit_pro

import pymysql
import os
import argparse
import requests
import urllib.parse
import sys
import time
import glob
import shutil
import tempfile

DECLARATOR_DOMAIN = 'https://declarator.org'


class TExportHumanFiles:

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--table", dest='table', default="declarations_documentfile")
        parser.add_argument("--document-file-id", dest='document_file_id', required=False)
        parser.add_argument("--tmp-folder", dest='tmp_folder', default=None)
        parser.add_argument("--dlrobot-human-json", dest='dlrobot_human_json', default="human_files.json")
        parser.add_argument("--start-from-an-empty-file", dest='start_from_empty', action="store_true", default=False)
        parser.add_argument("--max-files-count", dest='max_files_count', type=int)
        parser.add_argument("--mysql-port", dest='mysql_port', type=int, default=None)
        parser.add_argument("--pdf-conversion-timeout", dest='pdf_conversion_timeout',
                                default=1*60*60,
                                type=int,
                                help="pdf conversion timeout")
        parser.add_argument("--pdf-conversion-queue-limit", dest='pdf_conversion_queue_limit', type=int,
                            default=100 * 2 ** 20, help="max sum size of al pdf files that are in pdf conversion queue",
                            required=False)

        return parser.parse_args(arg_list)

    def __init__(self, args):
        self.logger = setup_logging(log_file_name="export_human_files.log")
        self.args = args
        if self.args.tmp_folder is None:
            self.args.tmp_folder = tempfile.mkdtemp("export_human")
            self.logger.debug("create folder {}".format(self.args.tmp_folder))
        else:
            self.logger.debug("rm folder {}".format(self.args.tmp_folder))
            shutil.rmtree(self.args.tmp_folder, ignore_errors=True)
            os.mkdir(self.args.tmp_folder)
        self.source_doc_client = TSourceDocClient(TSourceDocClient.parse_args([]), self.logger)
        self.pdf_conversion_client = TDocConversionClient(TDocConversionClient.parse_args([]), self.logger)
        self.smart_parser_server_client = TSmartParserCacheClient(TSmartParserCacheClient.parse_args([]), self.logger)
        self.new_pdfs = set()

    def __enter__(self):
        self.pdf_conversion_client.start_conversion_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.pdf_conversion_client.stop_conversion_thread()
        shutil.rmtree(self.args.tmp_folder, ignore_errors=True)

    def unarchive(self, input_file):
        base_name, file_extension = os.path.splitext(os.path.basename(input_file))
        output_folder = os.path.dirname(input_file)
        dearchiver = TDearchiver(self.logger, output_folder)
        for _, _, filename in dearchiver.dearchive_one_archive(file_extension, input_file, base_name):
            yield filename

    def download_file_and_unzip(self, file_url, filename):
        file_without_extension, extension = os.path.splitext(filename)
        if not os.path.isfile(filename):
            self.logger.debug("download {0}  to {1}".format(file_url, filename))
            result = requests.get(file_url)
            with open(filename, 'wb') as fd:
                fd.write(result.content)
            if extension == '.zip':
                try:
                    for archive_filename in self.unarchive(filename):
                        yield archive_filename
                except Exception as e:
                    self.logger.error("cannot unzip  {}, exception={}".format(filename, e))
            else:
                yield filename
        else:
            if extension == '.zip':
                for archive_filename in glob.glob("{}_*".format(file_without_extension)):
                    yield archive_filename
            else:
                yield filename

    def get_all_file_sql_records(self):
        if self.args.mysql_port is None:
            db = pymysql.connect(db="declarator", user="declarator", password="declarator", unix_socket="/var/run/mysqld/mysqld.sock" )
        else:
            db = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                 port=self.args.mysql_port)
        cursor = db.cursor()
        if self.args.document_file_id is not None:
            where_clause = "where f.id = {}\n".format(self.args.document_file_id)
        else:
            where_clause = ""
        query = ("""
                    select f.id, d.id, f.file, f.link, d.office_id, d.income_year 
                    from {} f
                    join declarations_document d on f.document_id=d.id
                    {} 
                 """.format(self.args.table, where_clause))
        self.logger.debug(query.replace("\n", " "))
        cursor.execute(query)
        for (document_file_id, document_id, filename, link, office_id, income_year) in cursor:
            if filename is not None and len(filename) > 0:
                yield document_file_id, document_id, filename, link, office_id, income_year

        cursor.close()
        db.close()

    def download_unzip_and_send_file_source_doc_server(self, declarator_url_path, document_file_id):
        path, declarator_filename = os.path.split(declarator_url_path)
        _, ext = os.path.splitext(declarator_filename)
        ext = ext.lower()
        temp_file = os.path.join(self.args.tmp_folder, "{}{}".format(document_file_id, ext))
        declarator_url = os.path.join(DECLARATOR_DOMAIN, "media", urllib.parse.quote(declarator_url_path))
        declarator_url = declarator_url.replace('\\', '/')

        for file_name in self.download_file_and_unzip(declarator_url, temp_file):
            self.source_doc_client.send_file(file_name)
            if file_name.lower().endswith('.pdf'):
                _, extension = os.path.splitext(file_name)
                self.pdf_conversion_client.start_conversion_task_if_needed(file_name, extension)
                self.new_pdfs.add(build_dislosures_sha256(file_name))
            else:
                self.smart_parser_server_client.send_file(file_name)
            yield file_name, declarator_url

        self.pdf_conversion_client.wait_all_tasks_to_be_sent()
        for f in os.listdir(self.args.tmp_folder):
            os.unlink(os.path.join(self.args.tmp_folder, f))

    def export_files(self):
        human_files_db = TDlrobotHumanFile(self.args.dlrobot_human_json, read_db=not self.args.start_from_empty)
        document_file_ids = set()
        for sha256, doc in human_files_db.get_all_documents():
            for ref in doc.decl_references:
                if ref.document_file_id is not None:
                    document_file_ids.add(ref.document_file_id)

        files_count = 0
        for document_file_id, document_id, file_path, link, office_id, income_year in self.get_all_file_sql_records():
            if document_file_id in document_file_ids:
                continue

            while self.pdf_conversion_client.server_is_too_busy():
                self.logger.error("wait pdf conversion_server for 5 minutes, last_pdf_conversion_queue_length={}".format(
                    self.pdf_conversion_client.last_pdf_conversion_queue_length
                ))
                time.sleep(5*60)

            web_site = urlsplit_pro(link).netloc
            if web_site.startswith('www.'):
                web_site = web_site[len('www.'):]

            if self.args.max_files_count is not None and files_count >= self.args.max_files_count:
                break
            self.logger.debug("export document_file_id={}".format(document_file_id))
            for local_file_path, declarator_url in self.download_unzip_and_send_file_source_doc_server(file_path,
                                                                                                    document_file_id):
                sha256 = build_dislosures_sha256(local_file_path)
                self.logger.debug("add {}, sha256={}".format(local_file_path, sha256))
                source_document = TSourceDocument()
                _, source_document.file_extension = os.path.splitext(local_file_path)
                ref = TDeclaratorReference()
                ref.document_id = document_id
                ref.document_file_id = document_file_id
                ref._site_url = web_site
                ref.office_id = office_id
                ref.income_year = income_year
                ref.document_file_url = declarator_url
                source_document.add_decl_reference(ref)
                human_files_db.add_source_document(sha256, source_document)
                files_count += 1
        self.logger.debug('added files count: {}'.format(files_count))
        human_files_db.write()
        self.send_new_pdfs_to_smart_parser()

    def send_new_pdfs_to_smart_parser(self):
        self.logger.debug("wait pdf conversion for {} seconds".format(self.args.pdf_conversion_timeout))
        self.pdf_conversion_client.wait_doc_conversion_finished(self.args.pdf_conversion_timeout)

        missed_pdf_count = 0
        received_pdf_count = 0
        for sha256 in self.new_pdfs:
            self.logger.debug("try to converted file for {}".format(sha256))
            handle, temp_filename = tempfile.mkstemp(suffix=".docx")
            os.close(handle)
            if self.pdf_conversion_client.retrieve_document(sha256, temp_filename):
                received_pdf_count += 1
                self.logger.debug("send the converted file to smart parser")
                self.smart_parser_server_client.send_file(temp_filename)
            else:
                self.logger.error("converted file is not received")
                missed_pdf_count += 1
            os.unlink(temp_filename)
        if missed_pdf_count > 0:
            self.logger.error('received_pdf_count = {}, missed_pdf_count={}'.format(received_pdf_count, missed_pdf_count))


def main():
    args = TExportHumanFiles.parse_args(sys.argv[1:])
    with TExportHumanFiles(args) as exporter:
        exporter.export_files()


if __name__ == '__main__':
    main()