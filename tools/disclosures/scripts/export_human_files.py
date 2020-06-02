import pymysql
import os
import argparse
import hashlib
import json
from urllib.parse import urlparse
from declarations.input_json_specification import dhjs
import logging
import zipfile
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
    parser.add_argument("--output-folder", dest='output_folder', default='./out.documentfile')
    parser.add_argument("--output-json", dest='output_file', default="human_files.json")
    parser.add_argument("--max-files-count", dest='max_files_count', type=int)
    return parser.parse_args()


def unzip_one_archive(logger, input_file):
    extensions = {".docx", ".doc", ".rtf", ".htm", ".html", '.xls', '.xlsx', '.pdf'}
    main_file_name, _ = os.path.splitext(input_file)
    with zipfile.ZipFile(input_file) as zf:
        for archive_index, zipinfo in enumerate(zf.infolist()):
            _, file_extension = os.path.splitext(zipinfo.filename)
            file_extension = file_extension.lower()
            if file_extension not in extensions:
                continue
            zipinfo.filename = os.path.realpath("{}_{}{}".format(main_file_name, archive_index, file_extension))
            logger.debug("unzip {}".format(zipinfo.filename))
            zf.extract(zipinfo)
            yield zipinfo.filename


def download_file_and_unzip(logger, file_url, filename):
    file_without_extension, extension = os.path.splitext(filename)
    if not os.path.isfile(filename):
        logger.debug("download {0}  to {1}".format(file_url, filename))
        result = requests.get(file_url)
        with open(filename, 'wb') as fd:
            fd.write(result.content)
        if extension == '.zip':
            try:
                for archive_filename in unzip_one_archive(logger, filename):
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


def get_all_files(tablename):
    db = pymysql.connect(db="declarator", user="declarator", password="declarator", unix_socket="/var/run/mysqld/mysqld.sock" )
    cursor = db.cursor()
    query = ("""
                select f.id, d.id, f.file, f.link, d.office_id, d.income_year 
                from {} f 
                join declarations_document d on f.document_id=d.id
             """.format(tablename))
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
    for file_name in download_file_and_unzip(logger, declarator_url, local_file_path):
        yield file_name


def get_all_files_by_table(logger, table_name, output_folder):
    for document_file_id, document_id, url_path, link, office_id, income_year in get_all_files(table_name):
        for local_file_path in export_file_to_folder(logger, url_path, document_file_id, output_folder):
            if not os.path.exists(local_file_path):
                logger.error("cannot find {}".format(local_file_path))
            else:
                yield document_file_id, document_id, link, local_file_path, office_id, income_year


def main(args):
    logger = setup_logging("download.log")
    files = {}
    if not os.path.exists(args.output_folder):
        logger.debug("create {}".format(args.output_folder))
        os.mkdir(args.output_folder)
    files_count = 0
    for document_file_id, document_id, link, file_path, office_id, income_year in get_all_files_by_table(logger, args.table, args.output_folder):
        sha256 = build_sha256(file_path)
        domain = urlparse(link).netloc
        if domain.startswith('www.'):
            domain = domain[len('www.'):]
        files[sha256] = {
                dhjs.declarator_document_id: document_id,
                dhjs.declarator_document_file_id: document_file_id,
                dhjs.declarator_web_domain: domain,
                dhjs.declarator_file_path: os.path.basename(file_path),
                dhjs.declarator_office_id: office_id,
                dhjs.declarator_income_year: income_year
        }
        files_count += 1
        if args.max_files_count is not None and files_count >= args.max_files_count:
            break

    with open(args.output_file, "w") as out:
        human_json = {
            dhjs.declarator_folder: args.output_folder,
            dhjs.file_collection: files
        }
        json.dump(human_json, out, indent=4)


if __name__ == '__main__':
    args = parse_args()
    main(args)