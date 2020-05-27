import pymysql
import os
import argparse
import hashlib
import json
import glob
from urllib.parse import urlparse
from declarations.dlrobot_human_common import dhjs


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", dest='file_folder', default='./files')
    parser.add_argument("--table", dest='table')
    parser.add_argument("--output-json", dest='output_file', default="converted_file_storage.json")
    return parser.parse_args()


def get_all_files(tablename):
    db = pymysql.connect(db="declarator", user="declarator", password="declarator", unix_socket="/var/run/mysqld/mysqld.sock" )
    cursor = db.cursor()
    query = ("select f.id, f.file, f.link, d.office_id from {0} f join declarations_document d on f.document_id=d.id;".format(tablename))
    cursor.execute(query)
    for (id, filename, link, office_id) in cursor:
        if filename is not  None and len(filename) > 0:
            yield id, filename, link, office_id

    cursor.close()
    db.close()


def build_sha256(filename):
    with open(filename, "rb") as f:
        file_data = f.read()
        return hashlib.sha256(file_data).hexdigest()


def get_all_files_by_table(table_name, folder):

    for document_id, url_path, link, office_id in get_all_files(table_name):
        path, filename = os.path.split(url_path)
        filename, ext = os.path.splitext(filename)
        ext = ext.lower()
        base_file = "%s%s" % (document_id, ext)
        local_file_path = os.path.join(folder, base_file)
        if not os.path.exists(local_file_path):
            print ("cannot find {}".format(local_file_path))
        else:
            if ext == ".zip":
                pattern = os.path.join(folder, "{}_*".format(document_id))
                for archive_filename in glob.glob(pattern):
                    yield link, archive_filename, office_id
            else:
                yield link, local_file_path, office_id


def main (args):
    files = {}
    for link, file_path, office_id in get_all_files_by_table(args.table, args.file_folder):
        sha256 = build_sha256(file_path)
        domain = urlparse(link).netloc
        if domain.startswith('www.'):
            domain = domain[len('www.'):]
        files[sha256] = {
                dhjs.web_domain: domain,
                dhjs.link: link,
                dhjs.filepath: file_path,
                dhjs.office_id: office_id
        }

    with open(args.output_file, "w") as out:
        json.dump(files, out, indent=4)


if __name__ == '__main__':
    args = parse_args()
    main(args)