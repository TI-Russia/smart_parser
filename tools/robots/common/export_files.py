from operator import itemgetter
from bs4 import BeautifulSoup
from itertools import groupby
import os
from collections import defaultdict
import logging
import shutil
import hashlib
from robots.common.archives import dearchive_one_archive, is_archive_extension
from robots.common.download import ACCEPTED_DECLARATION_FILE_EXTENSIONS,  \
    TDownloadedFile,  DEFAULT_HTML_EXTENSION
from DeclDocRecognizer.dlrecognizer import run_dl_recognizer, DL_RECOGNIZER_ENUM
import re

if shutil.which('unrar') is None:
    raise Exception("cannot find unrar (Copyright (c) 1993-2017 Alexander Roshal),\n sudo apt intall unrar")


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


def build_sha256(filename):
    with open(filename, "rb") as f:
        file_data = f.read()
        if filename.endswith(DEFAULT_HTML_EXTENSION):
            file_data = html_to_text(file_data).encode("utf-8", errors="ignore")
        return hashlib.sha256(file_data).hexdigest()


def export_one_file_tmp(url, cached_file, extension, index, office_folder):
    if extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        return
    logger = logging.getLogger("dlrobot_logger")
    export_path = os.path.join(office_folder, str(index) + ".tmp" + extension)
    if not os.path.exists(cached_file):
        logger.error("cannot find cached file {}, cache is broken or 404 on fetching?".format(cached_file))
        return
    if not os.path.exists(os.path.dirname(export_path)):
        os.makedirs(os.path.dirname(export_path))
    if is_archive_extension(extension):
        for archive_index, name_in_archive, export_filename in dearchive_one_archive(extension, cached_file, index, office_folder):
            logger.debug("export temporal file {}, archive_index: {} to {}".format(cached_file, archive_index, export_filename))
            yield {
                "url": url,
                "sha256": build_sha256(export_filename),
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
                "sha256": build_sha256(cached_file),
                "export_path": export_path,
                "cached_file": cached_file
        }


def check_html_can_be_declaration_preliminary(html):
    # dl_recognizer is called afterwards
    html = html.lower()
    words = html.find('квартир') != -1 and html.find('доход') != -1 and html.find('должность') != -1
    numbers = re.search('[0-9]{6}', html) is not None # доход
    return words and numbers


def export_last_step_docs(office_info, export_files):
    logger = logging.getLogger("dlrobot_logger")
    index = 0
    last_step_urls = office_info.robot_steps[-1].step_urls
    logger.debug("process {} urls in last step".format(len(last_step_urls)))
    office_folder = office_info.get_export_folder()
    for url in last_step_urls:
        downloaded_file = TDownloadedFile(url)

        if downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
            if not check_html_can_be_declaration_preliminary(downloaded_file.convert_html_to_utf8()):
                logger.debug("do not export {} because of preliminary check".format(url))
                continue

        for e in export_one_file_tmp(url, downloaded_file.data_file_path, downloaded_file.file_extension, index,  office_folder):
            e['parent'] = office_info.url_nodes[url]  # temporal link
            export_files.append(e)
            index += 1

    return index


def export_downloaded_docs(office_info, index, export_files):
    office_folder = office_info.get_export_folder()
    for url, url_info in office_info.url_nodes.items():
        for d in url_info.downloaded_files:
            cached_file = d['downloaded_file']
            extension = os.path.splitext(cached_file)[1]
            for e in export_one_file_tmp(url, cached_file, extension, index, office_folder):
                e['parent'] = d  # temporal link
                export_files.append(e)
                index += 1
    return index


def recognize_document_types(sorted_files):
    separate_files_to_dl_results = defaultdict(int)
    archives_to_dl_results = defaultdict(int)
    logger = logging.getLogger("dlrobot_logger")

    for sha256, group in groupby(sorted_files, itemgetter('sha256')):
        first_equal_file = list(group)[0]
        input_file = first_equal_file['export_path']
        logger.debug("run_dl_recognizer for {}".format(input_file))
        dl_recognizer_result = run_dl_recognizer(input_file).verdict

        separate_files_to_dl_results[sha256] = dl_recognizer_result
        if dl_recognizer_result == DL_RECOGNIZER_ENUM.POSITIVE:
            archives_to_dl_results[first_equal_file['cached_file']] += 1  #sum good files in each archive
    return separate_files_to_dl_results, archives_to_dl_results


def reorder_export_files_and_delete_non_declarations(office_folder, export_files):
    sorted_files = sorted(export_files, key=itemgetter('sha256'))
    separate_files_to_dl_results, archives_to_dl_results = recognize_document_types(sorted_files)
    logger = logging.getLogger("dlrobot_logger")
    exported_files = list()
    for sha256, group in groupby(sorted_files, itemgetter('sha256')):
        # make test results stable
        group = sorted(group, key=(lambda x: " ".join((x['url'], x.get('anchor_text', ""), x.get('engine', "")))))

        # in order to be more stable take a file with the shortest path (for example without prefix www.)
        # the files were already sorted
        path_lens = list(len(f['url']) for f in group)
        chosen_file = group[path_lens.index(min(path_lens))]

        old_file_name = chosen_file['export_path']
        dl_recognizer_result = separate_files_to_dl_results[sha256]

        if dl_recognizer_result != DL_RECOGNIZER_ENUM.POSITIVE:
            if archives_to_dl_results.get(chosen_file['cached_file'], 0) > 1:  # more than 1 document in archive are declarations
                dl_recognizer_result = DL_RECOGNIZER_ENUM.POSITIVE  # consider other documents to be also declarations
            else:
                logger.debug("remove temporally exported file cached:{} url: {}, since decl_recognizer=0".format(chosen_file['cached_file'], chosen_file['url'],))
                for r in group:
                    os.remove(r['export_path'])
                continue

        logger.debug("export url: {} cached: {}".format(chosen_file['url'], chosen_file['cached_file']))
        extension = os.path.splitext(old_file_name)[1]
        new_file_name = os.path.join(office_folder, str(len(exported_files)) + extension)
        shutil.copy2(old_file_name, new_file_name)  # copy and delete = rename

        for r in group:
            parent = r.pop('parent')
            # store the same people_count many times (all group) to all mirror nodes to run write_click_features
            if type(parent) == dict:
                parent["dl_recognizer_result"] = dl_recognizer_result
            else:
                parent.dl_recognizer_result = dl_recognizer_result

            os.remove(r['export_path'])

        chosen_file["dl_recognizer_result"] = dl_recognizer_result
        chosen_file['export_path'] = new_file_name.replace('\\', '/')  # to compare windows and unix
        exported_files.append(chosen_file)

    return exported_files


def export_files_to_folder(offices):
    for office_info in offices:
        office_folder = office_info.get_export_folder()

        export_files = list()
        index = export_last_step_docs(office_info, export_files)
        export_downloaded_docs(office_info, index, export_files)
        office_info.exported_files = reorder_export_files_and_delete_non_declarations(office_folder, export_files)

        office_info.logger.info("found {} files, exported {} files to {}".format(
            len(export_files),
            len(office_info.exported_files),
            office_folder))
