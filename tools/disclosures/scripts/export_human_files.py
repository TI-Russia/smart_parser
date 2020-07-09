from declarations.input_json import TSourceDocument, TDeclaratorReference,  TDlrobotHumanFile, TIntersectionStatus
from robots.common.archives import  dearchive_one_archive

import pymysql
import os
import argparse
import hashlib
from urllib.parse import urlparse
import logging
import requests
import urllib.parse
import glob


DECLARATOR_DOMAIN = 'https://declarator.org'


def setup_logging(logfilename):
    logger = logging.getLogger("export")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", dest='table', default="declarations_documentfile")
    parser.add_argument("--document-file-id", dest='document_file_id', required=False)
    parser.add_argument("--output-folder", dest='output_folder', default='./out.documentfile')
    parser.add_argument("--output-json", dest='output_file', default="human_files.json")
    parser.add_argument("--max-files-count", dest='max_files_count', type=int)
    parser.add_argument("--mysql-port", dest='mysql_port', type=int, default=None)
    return parser.parse_args()


def unzip_one_archive(input_file):
    base_name, file_extension = os.path.splitext(os.path.basename(input_file))
    output_folder = os.path.dirname(input_file)
    for _, _, filename in dearchive_one_archive(file_extension, input_file, base_name, output_folder):
        yield filename


def download_file_and_unzip(logger, file_url, filename):
    file_without_extension, extension = os.path.splitext(filename)
    if not os.path.isfile(filename):
        logger.debug("download {0}  to {1}".format(file_url, filename))
        result = requests.get(file_url)
        with open(filename, 'wb') as fd:
            fd.write(result.content)
        if extension == '.zip':
            try:
                for archive_filename in unzip_one_archive(filename):
                    yield archive_filename
            except Exception as e:
                logger.error("cannot unzip  {}, exception={}".format(filename, e))
        else:
            yield filename
    else:
        if extension == '.zip':
            for archive_filename in glob.glob("{}_*".format(file_without_extension)):
                yield archive_filename
        else:
            yield filename


def get_all_file_sql_records(logger, args):
    if args.mysql_port is  None:
        db = pymysql.connect(db="declarator", user="declarator", password="declarator", unix_socket="/var/run/mysqld/mysqld.sock" )
    else:
        db = pymysql.connect(db="declarator", user="declarator", password="declarator",
                             port=args.mysql_port)
    cursor = db.cursor()
    if args.document_file_id is not None:
        where_clause = "where f.id = {}\n".format(args.document_file_id)
    else:
        where_clause = ""
    query = ("""
                select f.id, d.id, f.file, f.link, d.office_id, d.income_year 
                from {} f
                join declarations_document d on f.document_id=d.id
                {} 
             """.format(args.table, where_clause))
    logger.debug(query.replace("\n", " "))
    cursor.execute(query)
    for (document_file_id, document_id, filename, link, office_id, income_year) in cursor:
        if filename is not  None and len(filename) > 0:
            yield document_file_id, document_id, filename, link, office_id, income_year

    cursor.close()
    db.close()


def build_sha256(filename):
    with open(filename, "rb") as f:
        file_data = f.read()
        return hashlib.sha256(file_data).hexdigest()


def export_file_to_folder(logger, declarator_url_path, document_file_id, out_folder):
    global DECLARATOR_DOMAIN
    path, filename = os.path.split(declarator_url_path)
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    base_file = "{}{}".format(document_file_id, ext)
    local_file_path = os.path.join(out_folder, base_file)
    declarator_url = os.path.join(DECLARATOR_DOMAIN, "media", urllib.parse.quote(declarator_url_path))
    declarator_url = declarator_url.replace('\\', '/')

    for file_name in download_file_and_unzip(logger, declarator_url, local_file_path):
        yield file_name, declarator_url


def build_declarator_squeezes(logger, args):
    dlrobot_humam = TDlrobotHumanFile()
    dlrobot_humam.document_folder = args.output_folder
    files_count = 0
    for document_file_id, document_id, file_path, link, office_id, income_year in get_all_file_sql_records(logger, args):
        web_site = urlparse(link).netloc
        if web_site.startswith('www.'):
            web_site = web_site[len('www.'):]

        if args.max_files_count is not None and files_count >= args.max_files_count:
            break
        logger.debug("export document_file_id={}".format(document_file_id))
        for local_file_path, declarator_url in export_file_to_folder(logger, file_path, document_file_id, args.output_folder):
            if not os.path.exists(local_file_path):
                logger.error("cannot find {}".format(local_file_path))
            else:
                sha256 = build_sha256(local_file_path)
                source_document = TSourceDocument()
                source_document.intersection_status = TIntersectionStatus.only_human
                source_document.document_path = os.path.basename(local_file_path)
                ref = TDeclaratorReference()
                ref.document_id = document_id
                ref.document_file_id = document_file_id
                ref.web_domain = web_site
                ref.office_id = office_id
                ref.income_year = income_year
                ref.document_file_url = declarator_url
                source_document.references.append(ref)
                dlrobot_humam.add_source_document(sha256, source_document)
                files_count += 1
    return dlrobot_humam


def main(args):
    logger = setup_logging("download.log")
    if not os.path.exists(args.output_folder):
        logger.debug("create {}".format(args.output_folder))
        os.mkdir(args.output_folder)
    human_json = build_declarator_squeezes(logger, args)
    human_json.write(args.output_file)


if __name__ == '__main__':
    args = parse_args()
    main(args)