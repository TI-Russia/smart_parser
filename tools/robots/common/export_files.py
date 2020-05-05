from bs4 import BeautifulSoup
import os
from collections import defaultdict
import shutil
import hashlib
from robots.common.archives import dearchive_one_archive, is_archive_extension
from robots.common.download import ACCEPTED_DECLARATION_FILE_EXTENSIONS, TDownloadEnv
from robots.common.content_types import DEFAULT_HTML_EXTENSION, DEFAULT_PDF_EXTENSION
from DeclDocRecognizer.dlrecognizer import run_dl_recognizer, DL_RECOGNIZER_ENUM
import re
import copy


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


class TExportFile:
    def __init__(self, parent_record=None, url=None, cached_file=None, export_path=None,
                 archive_index=-1, name_in_archive=None, init_json=None):
        self.parent_record = parent_record
        self.url = url
        self.cached_file = cached_file
        self.export_path = export_path
        self.archive_index = archive_index
        self.name_in_archive = name_in_archive
        self.sha256 = None
        if init_json is not None:
            self.from_json(init_json)
        else:
            self.sha256 = build_sha256(export_path)
        self.file_extension = os.path.splitext(self.export_path)[1]

    def to_json(self):
        return {
            "url": self.url,
            "cached_file": self.cached_file,
            "export_path": self.export_path.replace('\\', '/'),  # to compare windows and unix,
            "archive_index": self.archive_index,
            "sha256": self.sha256
        }

    def from_json(self, rec):
        self.url = rec["url"]
        self.cached_file = rec["cached_file"]
        self.export_path = rec["export_path"]
        self.archive_index = rec["archive_index"]
        self.sha256 = rec["sha256"]


class TExportFileSet:
    def __init__(self, first_file):
        self.file_copies = [first_file]
        self.dl_recognizer_result = DL_RECOGNIZER_ENUM.UNKNOWN
        self.waiting_conversion = False

    def run_dl_recognizer_wrapper(self):
        self.dl_recognizer_result = run_dl_recognizer(self.file_copies[0].export_path).verdict


def export_one_file_tmp(office_info, url, cached_file, extension, parent_record):
    if extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        return
    index = office_info.sent_to_export_files_count
    office_info.sent_to_export_files_count += 1
    office_folder = office_info.get_export_folder()
    logger = office_info.logger
    export_path = os.path.join(office_folder, str(index) + ".tmp" + extension)
    if not os.path.exists(cached_file):
        logger.error("cannot find cached file {}, cache is broken or 404 on fetching?".format(cached_file))
        return
    new_files = list()
    if is_archive_extension(extension):
        for archive_index, name_in_archive, export_filename in dearchive_one_archive(extension, cached_file, index, office_folder):
            logger.debug("export temporal file {}, archive_index: {} to {}".format(cached_file, archive_index, export_filename))
            new_files.append(TExportFile(parent_record, url, cached_file, export_filename, name_in_archive,  archive_index))

    else:
        logger.debug("export temporal file {} to {}".format(cached_file, export_path))
        shutil.copyfile(cached_file, export_path)
        new_files.append(TExportFile(parent_record, url, cached_file, export_path))

    for new_file in new_files:
        found_file = office_info.export_files_by_sha256.get(new_file.sha256)
        if found_file is None:
            file_set = TExportFileSet(new_file)
            logger.debug("run_dl_recognizer for {}".format(new_file.export_path))
            if new_file.file_extension == DEFAULT_PDF_EXTENSION and \
                not TDownloadEnv.CONVERSION_CLIENT.check_file_was_converted(new_file.sha256):
                file_set.waiting_conversion = True
            else:
                file_set.run_dl_recognizer_wrapper()
            office_info.export_files_by_sha256[new_file.sha256] = file_set
        else:
            found_file.file_copies.append(new_file)


def check_html_can_be_declaration_preliminary(html):
    # dl_recognizer is called afterwards
    html = html.lower()
    words = html.find('квартир') != -1 and html.find('доход') != -1 and html.find('должность') != -1
    numbers = re.search('[0-9]{6}', html) is not None # доход
    return words and numbers


# more than 1 document in archive are declarations
# consider other documents to be also declarations
def set_archive_contain_declarations_if_two_files_are_declarations(office_info):
    logger = office_info.logger
    archives_to_dl_results = defaultdict(set)
    for sha256, file_set in office_info.export_files_by_sha256.items():
        for f in file_set.file_copies:
            if f.archive_index != -1 and file_set.dl_recognizer_result == DL_RECOGNIZER_ENUM.POSITIVE:
                archives_to_dl_results[f.cached_file].add(sha256)
    for sha256, file_set in office_info.export_files_by_sha256.items():
        if file_set.dl_recognizer_result != DL_RECOGNIZER_ENUM.POSITIVE:
            for f in file_set.file_copies:
                if f.archive_index != -1 and len(archives_to_dl_results[f.cached_file]) > 1:
                    file_set.dl_recognizer_result = DL_RECOGNIZER_ENUM.POSITIVE
                    logger.debug("set dl_recognizer_result to {} for {} because other files in a archive are declarations".format(
                        file_set.dl_recognizer_result, sha256))
                    break


def run_postponed_dl_recognizers(office_info):
    for sha256, file_set in office_info.export_files_by_sha256.items():
        if file_set.waiting_conversion:
            file_set.run_dl_recognizer_wrapper()
            file_set.waiting_conversion = False


def reorder_export_files_and_delete_non_declarations(office_info):
    run_postponed_dl_recognizers(office_info)
    set_archive_contain_declarations_if_two_files_are_declarations(office_info)
    office_folder = office_info.get_export_folder()
    logger = office_info.logger
    office_info.exported_files = list()
    for sha256, file_set in office_info.export_files_by_sha256.items():
        # make test results stable
        if file_set.dl_recognizer_result == DL_RECOGNIZER_ENUM.POSITIVE:
            file_set.file_copies.sort(key=(lambda x: (len(x.url), x.url, x.archive_index)), reverse=True)
            chosen_file = copy.copy(file_set.file_copies[0])
            logger.debug("export url: {} cached: {}".format(chosen_file.url, chosen_file.cached_file))
            old_file_name = chosen_file.export_path
            new_file_name = os.path.join(office_folder, str(len(office_info.exported_files)) + chosen_file.file_extension)
            shutil.copy2(old_file_name, new_file_name)  # copy
            chosen_file.export_path = new_file_name
            office_info.exported_files.append(chosen_file)

        for r in file_set.file_copies:
            r.parent_record.dl_recognizer_result = file_set.dl_recognizer_result # copy to click graph
            logger.debug("remove temporally exported file cached:{} url: {}".format(r.export_path, r.url))
            os.remove(r.export_path)


def export_files_to_folder(offices):
    for office_info in offices:
        reorder_export_files_and_delete_non_declarations(office_info)

        office_info.logger.info("found {} files, exported {} files to {}".format(
            office_info.sent_to_export_files_count,
            len(office_info.exported_files),
            office_info.get_export_folder()))
