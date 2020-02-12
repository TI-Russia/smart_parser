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

UNKNOWN_PEOPLE_COUNT = -1


def process_smart_parser_json(json_file):
    with open(json_file, "r", encoding="utf8") as inpf:
        smart_parser_json = json.load(inpf)
        people_count = len(smart_parser_json.get("persons", []))
    os.remove(json_file)
    return people_count


def get_people_count_from_smart_parser(smart_parser_binary, inputfile):
    people_count = UNKNOWN_PEOPLE_COUNT
    if smart_parser_binary == "none":
        return people_count
    if inputfile.endswith("pdf"): # cannot process new pdf without conversion
        return people_count
    logger = logging.getLogger("dlrobot_logger")
    cmd = "{} -skip-relative-orphan -skip-logging  -adapter prod -fio-only {}".format(smart_parser_binary, inputfile)
    logger.debug(cmd)
    os.system(cmd)
    json_file = inputfile + ".json"
    if os.path.exists(json_file):
        people_count = process_smart_parser_json(json_file)
    else:
        sheet_index = 0
        while True:
            json_file = "{}_{}.json".format(inputfile, sheet_index)
            if not os.path.exists(json_file):
                break
            if people_count == UNKNOWN_PEOPLE_COUNT:
                people_count = 0
            people_count += process_smart_parser_json(json_file)
            sheet_index += 1

    converted_file = inputfile + ".converted.docx"
    if os.path.exists(converted_file):
        os.remove(converted_file)

    return people_count


def unzip_one_file(input_file, main_index, outfolder):
    zip_file = zipfile.ZipFile(input_file)
    for index, filename in enumerate(zip_file.namelist()):
        _, file_extension = os.path.splitext(filename)
        file_extension = file_extension.lower()
        if file_extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
            continue
        old_file_name = zip_file.extract(filename, outfolder)
        new_file_name = os.path.join(outfolder, "{}_{}{}".format(main_index, index, file_extension))
        os.rename(old_file_name,  new_file_name)
        yield new_file_name
    zip_file.close()


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
        logger.error("cannot find cached file {}, cache is broken?".format(cached_file))
        return
    if not os.path.exists(os.path.dirname(export_path)):
        os.makedirs(os.path.dirname(export_path))
    if extension == DEFAULT_ZIP_EXTENSION:
        for filename in unzip_one_file(cached_file, index, office_folder):
            yield {
                "url": url,
                "sha256": build_sha256(filename, os.path.splitext(filename)[1]),
                "cached_file": cached_file,
                "export_path": filename,
                "archive_index": index
            }
    else:
        shutil.copyfile(cached_file, export_path)
        yield {
                "url": url,
                "sha256": build_sha256(cached_file, extension),
                "export_path": export_path,
                "cached_file": cached_file,
                "archive_index": -1
        }


def sha256_key_and_url(r):
    return r["sha256"], len(r["url"]), r["url"], r["archive_index"]


def export_files_to_folder(offices, smart_parser_binary, outfolder):
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
            logger.debug("export url: {} cached: {}".format(first_equal_file['url'], first_equal_file['cached_file']))
            people_count = get_people_count_from_smart_parser(smart_parser_binary, old_file_name)
            extension = os.path.splitext(old_file_name)[1]
            new_file_name = os.path.join(office_folder, str(index) + extension)
            shutil.copy2(old_file_name, new_file_name) # copy and delete = rename

            for r in group:
                parent = r.pop('parent')
                # store the same people_count many times (all group) to all mirror nodes to run write_click_features
                if type(parent) == dict:
                    parent["people_count"] = people_count
                else:
                    parent.people_count = people_count

                os.remove(r['export_path'])

            first_equal_file["people_count"] = people_count
            first_equal_file['export_path'] = new_file_name.replace('\\', '/') # to compare windows and unix

            office_info.exported_files.append( first_equal_file )

        logger.info("found {} files, exported {} files to {}".format(
            len(export_files),
            len(office_info.exported_files),
            office_folder))
