import requests
import json
import logging
from requests.auth import HTTPBasicAuth
import os
import sys
import argparse
import pymysql
import urllib.parse
import argparse
import zipfile

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(0)
declarator_domain = 'https://declarator.org'
#declarator_domain = 'declarator.org'

client = requests.Session()
credentials = json.load(open('auth.json'))
client.auth = HTTPBasicAuth(credentials['username'], credentials['password'])


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", dest='table')
    parser.add_argument("--output-folder", dest='output_folder')
    parser.add_argument("--prefix", dest='prefix')
    return parser.parse_args()



def unzip_one_archive(input_file):
    extensions = {".docx", ".doc", ".rtf", ".htm", ".html", '.xls', '.xlsx', '.pdf'}
    main_file_name, _ = os.path.splitext(input_file)
    with zipfile.ZipFile(input_file) as zf:
        for archive_index, zipinfo in enumerate(zf.infolist()):
            _, file_extension = os.path.splitext(zipinfo.filename)
            file_extension = file_extension.lower()
            if file_extension not in extensions:
                continue
            zipinfo.filename = "{}_{}{}".format(main_file_name, archive_index, file_extension)
            print ("unzip {}".format(zipinfo.filename))
            zf.extract(zipinfo)


def download_file(file_url, filename):
    if os.path.isfile(filename) and os.path.getsize(filename) != 162:
        return
    path, _ = os.path.split(filename)
    os.makedirs(path, exist_ok=True)
    print ("download {0}  to {1}".format(file_url, filename))
    result = requests.get(file_url)
    with open(filename, 'wb') as fd:
        fd.write(result.content)

    if filename.endswith('.zip'):
        try:
            unzip_one_archive(filename)
        except Exception as e:
            print ("cannot unzip  " +  filename + " " + str(e) )
   


def get_all_files(tablename):
    db = pymysql.connect(db="declarator",user="declarator",password="declarator", unix_socket="/var/run/mysqld/mysqld.sock" )
    cursor = db.cursor()
    query = ("select id, file from  {0};".format(tablename))
    cursor.execute(query)
    for (id, filename) in cursor:
        if filename != None and len(filename) > 0:
            yield (id, filename)

    cursor.close()
    db.close()

def get_all_files_by_table(tablename, outfolder, outfileprefix):

    for document_id, url_path in get_all_files(tablename):
        path, filename = os.path.split(url_path)
        filename, ext = os.path.splitext(filename)
        ext = ext.lower()
        base_file = "%s%s" % (document_id, ext)
        if outfileprefix is not None:
            base_file = outfileprefix + base_file
        local_file_path = os.path.join(outfolder, base_file)

        url_path =  urllib.parse.quote(url_path)
        download_file(os.path.join(declarator_domain, "media", url_path), local_file_path)

if __name__ == '__main__':
    args = parse_args()
    get_all_files_by_table(args.table, args.output_folder, args.prefix)

      

