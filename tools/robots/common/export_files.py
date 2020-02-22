import json
from operator import itemgetter
from bs4 import BeautifulSoup
from itertools import groupby
import os
import logging
import zipfile
import shutil
import hashlib
from download import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_ZIP_EXTENSION, \
    get_file_extension_by_cached_url, get_local_file_name_by_url, DEFAULT_HTML_EXTENSION

DECL_RECOGNIZER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    os.path.normpath("../../DeclDocRecognizer/dlrecognizer.sh"))
if not os.path.exists(DECL_RECOGNIZER_PATH):
    raise Exception("cannot find {} ".format(DECL_RECOGNIZER_PATH))

DL_RECOGNIZER_UNKNOWN = -1
DL_RECOGNIZER_POSITIVE = 1
DL_RECOGNIZER_NEGATIVE = 0


def run_decl_recognizer(inputfile):
    global DECL_RECOGNIZER_PATH
    logger = logging.getLogger("dlrobot_logger")
    json_file = inputfile + ".json"
    cmd = "bash {} {} {}".format(DECL_RECOGNIZER_PATH, inputfile, json_file)
    logger.debug(cmd)
    os.system(cmd)
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf8") as inpf:
            recognizer_result = json.load(inpf).get("result", "unknown")
        os.remove(json_file)
        if recognizer_result == "declaration":
            return DL_RECOGNIZER_POSITIVE
        elif recognizer_result == "some_other_document":
            return DL_RECOGNIZER_NEGATIVE
    return DL_RECOGNIZER_UNKNOWN


def unzip_one_archive(input_file, main_index, outfolder):
    with zipfile.ZipFile(input_file) as zf:
        for archive_index, zipinfo in enumerate(zf.infolist()):
            _, file_extension = os.path.splitext(zipinfo.filename)
            file_extension = file_extension.lower()
            if file_extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
                continue
            old_file_name = zipinfo.filename
            zipinfo.filename = os.path.join(outfolder, "{}_{}{}".format(main_index, archive_index, file_extension))
            zf.extract(zipinfo)
            yield archive_index, old_file_name, zipinfo.filename



def html_to_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.find_all(text=True)
    blacklist = [
        '[document]',
        'noscript',
        'header',
        'html',
        'meta',
        'head',
        'input',
        'script',
        'style',
    ]

    output = ''
    for t in text:
        if t.parent.name not in blacklist:
            output += '{} '.format(t)
    return output


def build_sha256(filename, extension):
    with open(filename, "rb") as f:
        file_data = f.read()
        if filename.endswith(DEFAULT_HTML_EXTENSION):
            file_data = html_to_text(file_data).encode("utf-8", errors="ignore")
        return hashlib.sha256(file_data).hexdigest()


def export_one_file_tmp(url, index, cached_file, extension, office_folder):
    logger = logging.getLogger("dlrobot_logger")
    export_path = os.path.join(office_folder, str(index) + ".tmp" + extension)
    if extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        return
    if not os.path.exists(cached_file):
        logger.error("cannot find cached file {}, cache is broken or 404 on fetching?".format(cached_file))
        return
    if not os.path.exists(os.path.dirname(export_path)):
        os.makedirs(os.path.dirname(export_path))
    if extension == DEFAULT_ZIP_EXTENSION:
        for archive_index, name_in_archive, export_filename in unzip_one_archive(cached_file, index, office_folder):
            logger.debug("export temporal file {}, archive_index: {} to {}".format(cached_file, archive_index, export_filename))
            yield {
                "url": url,
                "sha256": build_sha256(export_filename, os.path.splitext(export_filename)[1]),
                "cached_file": cached_file,
                "export_path": export_filename,
                "name_in_archive": name_in_archive,
                "archive_index": archive_index
            }
    else:
        logger.debug("export temporal file {} to {}".format(cached_file, export_path))
        shutil.copyfile(cached_file, export_path)
        yield {
                "url": url,
                "sha256": build_sha256(cached_file, extension),
                "export_path": export_path,
                "cached_file": cached_file
        }


def sha256_key_and_url(r):
    return r["sha256"], len(r["url"]), r["url"], r.get("archive_index", -1)


def export_files_to_folder(offices, outfolder):
    logger = logging.getLogger("dlrobot_logger")
    for office_info in offices:
        office_folder = os.path.join(outfolder, office_info.get_domain_name())
        if os.path.exists(office_folder):
            shutil.rmtree(office_folder)
        index = 0
        export_files = list()
        last_step_urls = office_info.robot_steps[-1].step_urls
        logger.debug("process {} urls in last step".format(len(last_step_urls)))
        for url in last_step_urls:
            extension = get_file_extension_by_cached_url(url)
            cached_file = get_local_file_name_by_url(url)
            for e in export_one_file_tmp (url, index, cached_file, extension, office_folder):
                e['parent'] = office_info.url_nodes[url]  # temporal link
                export_files.append(e)
                index += 1


        for url, url_info in office_info.url_nodes.items():
            for d in url_info.downloaded_files:
                cached_file = d['downloaded_file']
                extension = os.path.splitext(cached_file)[1]
                for e in export_one_file_tmp(url, index, cached_file, extension, office_folder):
                    e['parent'] = d  # temporal link
                    export_files.append(e)
                    index += 1


        sorted_files = sorted (export_files, key=sha256_key_and_url)
        office_info.exported_files = list()
        for _, group in groupby(sorted_files, itemgetter('sha256')):
            index = len(office_info.exported_files)
            group = list(group)
            first_equal_file = group[0]
            old_file_name = first_equal_file['export_path']
            dl_recognizer_result = run_decl_recognizer(old_file_name)

            if dl_recognizer_result == DL_RECOGNIZER_NEGATIVE:
                for r in group:
                    os.remove(r['export_path'])
                continue

            logger.debug("export url: {} cached: {}".format(first_equal_file['url'], first_equal_file['cached_file']))
            extension = os.path.splitext(old_file_name)[1]
            new_file_name = os.path.join(office_folder, str(index) + extension)
            shutil.copy2(old_file_name, new_file_name) # copy and delete = rename

            for r in group:
                parent = r.pop('parent')
                # store the same people_count many times (all group) to all mirror nodes to run write_click_features
                if type(parent) == dict:
                    parent["dl_recognizer_result"] = dl_recognizer_result
                else:
                    parent.dl_recognizer_result = dl_recognizer_result

                os.remove(r['export_path'])

            first_equal_file["dl_recognizer_result"] = dl_recognizer_result
            first_equal_file['export_path'] = new_file_name.replace('\\', '/') # to compare windows and unix

            office_info.exported_files.append( first_equal_file )

        logger.info("found {} files, exported {} files to {}".format(
            len(export_files),
            len(office_info.exported_files),
            office_folder))
