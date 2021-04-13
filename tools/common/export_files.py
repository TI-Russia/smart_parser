from common.primitives import build_dislosures_sha256
from common.archives import TDearchiver
from common.download import ACCEPTED_DECLARATION_FILE_EXTENSIONS, TDownloadEnv, TDownloadedFile
from common.content_types import DEFAULT_HTML_EXTENSION, DEFAULT_PDF_EXTENSION
from DeclDocRecognizer.dlrecognizer import run_dl_recognizer, DL_RECOGNIZER_ENUM
from common.find_link import TLinkInfo

import re
import copy
import time
import os
from collections import defaultdict
import shutil


class TExportFile:
    def __init__(self, link_info : TLinkInfo = None, url=None, cached_file=None, export_path=None,
                 archive_index: int = -1, name_in_archive:str=None, init_json=None):
        self.last_link_info = link_info
        self.url = url
        self.cached_file = cached_file
        self.export_path = export_path
        self.archive_index = archive_index
        self.name_in_archive = name_in_archive
        self.sha256 = None
        if init_json is not None:
            self.from_json(init_json)
        else:
            self.sha256 = build_dislosures_sha256(export_path)
        self.file_extension = os.path.splitext(self.export_path)[1]
        self.smart_parser_json_sha256 = None

    def to_json(self):
        return {
            "url": self.url,
            "cached_file": self.cached_file,
            "export_path": self.export_path.replace('\\', '/'),  # to compare windows and unix,
            "archive_index": self.archive_index,
            "sha256": self.sha256,
            "smart_parser_json_sha256": self.smart_parser_json_sha256
        }

    def from_json(self, rec):
        self.url = rec["url"]
        self.cached_file = rec["cached_file"]
        self.export_path = rec["export_path"]
        self.sha256 = rec["sha256"]
        self.archive_index = rec.get("archive_index", -1)
        self.smart_parser_json_sha256 = rec.get("smart_parser_json_sha256")


class TExportFileSet:
    def __init__(self, first_file):
        self.file_copies = [first_file]
        self.dl_recognizer_result = DL_RECOGNIZER_ENUM.UNKNOWN
        self.waiting_conversion = False

    def run_dl_recognizer_wrapper(self, logger):
        try:
            self.dl_recognizer_result = DL_RECOGNIZER_ENUM.UNKNOWN
            logger.debug("run_dl_recognizer for {}".format(self.file_copies[0].export_path))
            self.dl_recognizer_result = run_dl_recognizer(self.file_copies[0].export_path).verdict
        except Exception as exp:
            logger.error(exp)


def check_html_can_be_declaration_preliminary(downloaded_file):
    # dl_recognizer is called afterwards
    try:
        html = downloaded_file.convert_html_to_utf8()
    except ValueError as exp:
        # cannot find encoding
        return False
    html = html.lower()
    words = html.find('квартир') != -1 and html.find('доход') != -1 and html.find('должность') != -1
    numbers1 = re.search('[0-9]{6}', html) is not None # доход
    numbers2 = re.search('[0-9]{3}\s[0-9]{3}', html) is not None  # доход
    return words and (numbers1 or numbers2)


class TExportEnvironment:
    def __init__(self, website):
        self.website = website
        self.logger = website.logger
        self.sent_to_export_files_count = 0
        self.export_files_by_sha256 = dict()
        self.exported_files = list()
        self.exported_urls = set()
        self.last_found_declaration_time = time.time()

    def to_json(self):
        return list(x.to_json() for x in self.exported_files)

    def from_json(self, rec):
        self.exported_files = list()
        if rec is not None:
            self.exported_files = list(TExportFile(init_json=x) for x in rec)

    # todo: do not save file copies
    def export_one_file_or_send_to_conversion(self, url, cached_file, extension, link_info):
        if extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
            return
        index = self.sent_to_export_files_count
        self.sent_to_export_files_count += 1
        office_folder = self.website.get_export_folder()
        export_path = os.path.join(office_folder, str(index) + ".tmp" + extension)
        if not os.path.exists(cached_file):
            self.logger.error("cannot find cached file {}, cache is broken or 404 on fetching?".format(cached_file))
            return
        new_files = list()
        if TDearchiver.is_archive_extension(extension):
            dearchiver = TDearchiver(self.logger, office_folder)
            for archive_index, name_in_archive, export_filename in dearchiver.dearchive_one_archive(extension, cached_file, index):
                self.logger.debug("export temporal file {}, archive_index: {} to {}".format(cached_file, archive_index, export_filename))
                new_files.append(TExportFile(link_info, url, cached_file, export_filename, archive_index, name_in_archive))

        else:
            self.logger.debug("export temporal file {} to {}".format(cached_file, export_path))
            shutil.copyfile(cached_file, export_path)
            new_files.append(TExportFile(link_info, url, cached_file, export_path))

        for new_file in new_files:
            found_file = self.export_files_by_sha256.get(new_file.sha256)
            if found_file is None:
                file_set = TExportFileSet(new_file)
                self.logger.debug("run_dl_recognizer for {}".format(new_file.export_path))
                if new_file.file_extension == DEFAULT_PDF_EXTENSION  \
                    and TDownloadEnv.CONVERSION_CLIENT is not None \
                    and not TDownloadEnv.CONVERSION_CLIENT.check_file_was_converted(new_file.sha256):
                    file_set.waiting_conversion = True
                else:
                    file_set.run_dl_recognizer_wrapper(self.logger)
                    if file_set.dl_recognizer_result == DL_RECOGNIZER_ENUM.POSITIVE:
                        self.last_found_declaration_time = time.time()
                        self.logger.debug("found a declaration")
                self.export_files_by_sha256[new_file.sha256] = file_set
            else:
                found_file.file_copies.append(new_file)

    def export_file_if_relevant(self, downloaded_file: TDownloadedFile, link_info: TLinkInfo):
        url = downloaded_file.original_url
        if url in self.exported_urls:
            return
        self.exported_urls.add(url)

        if downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
            if not check_html_can_be_declaration_preliminary(downloaded_file):
                self.logger.debug("do not export {} because of preliminary check".format(url))
                return

        self.export_one_file_or_send_to_conversion(url, downloaded_file.data_file_path, downloaded_file.file_extension, link_info)

    def export_selenium_doc_if_relevant(self, link_info: TLinkInfo):
        cached_file = link_info.downloaded_file
        extension = os.path.splitext(cached_file)[1]
        self.export_one_file_or_send_to_conversion(link_info.source_url, cached_file, extension, link_info)

    # more than 1 document in archive are declarations
    # consider other documents to be also declarations
    def set_archive_contain_declarations_if_two_files_are_declarations(self):
        archives_to_dl_results = defaultdict(set)
        for sha256, file_set in self.export_files_by_sha256.items():
            for f in file_set.file_copies:
                if f.archive_index != -1 and file_set.dl_recognizer_result == DL_RECOGNIZER_ENUM.POSITIVE:
                    archives_to_dl_results[f.cached_file].add(sha256)
        for sha256, file_set in self.export_files_by_sha256.items():
            if file_set.dl_recognizer_result != DL_RECOGNIZER_ENUM.POSITIVE:
                for f in file_set.file_copies:
                    if f.archive_index != -1 and len(archives_to_dl_results[f.cached_file]) > 1:
                        file_set.dl_recognizer_result = DL_RECOGNIZER_ENUM.POSITIVE
                        self.logger.debug("set dl_recognizer_result to {} for {} because other files in a archive are declarations".format(
                            file_set.dl_recognizer_result, sha256))
                        break

    def run_postponed_dl_recognizers(self):
        for sha256, file_set in self.export_files_by_sha256.items():
            if not self.website.parent_project.have_time_for_last_dl_recognizer():
                self.logger.error("stop running dl_recognizer, because there is no time")
                break
            if file_set.waiting_conversion:
                file_set.run_dl_recognizer_wrapper(self.logger)
                file_set.waiting_conversion = False

    def reorder_export_files_and_delete_non_declarations(self):
        self.run_postponed_dl_recognizers()
        self.set_archive_contain_declarations_if_two_files_are_declarations()
        office_folder = self.website.get_export_folder()
        self.exported_files = list()
        self.logger.debug("start proccessing {} temporally exported files".format(len(self.export_files_by_sha256.keys())))
        for sha256, file_set in self.export_files_by_sha256.items():
            # make test results stable
            if file_set.dl_recognizer_result == DL_RECOGNIZER_ENUM.POSITIVE:
                file_set.file_copies.sort(key=(lambda x: (len(x.url), x.url, x.archive_index)))
                chosen_file = copy.copy(file_set.file_copies[0])
                self.logger.debug("export url: {} cached: {}".format(chosen_file.url, chosen_file.cached_file))
                old_file_name = chosen_file.export_path
                new_file_name = os.path.join(office_folder, str(len(self.exported_files)) + chosen_file.file_extension)
                shutil.copy2(old_file_name, new_file_name)  # copy
                chosen_file.export_path = new_file_name
                self.exported_files.append(chosen_file)

            for r in file_set.file_copies:
                r.last_link_info.dl_recognizer_result = file_set.dl_recognizer_result # copy to click graph
                self.logger.debug("remove temporally exported file cached:{} url: {}".format(r.export_path, r.url))
                os.remove(r.export_path)

        self.logger.info("found {} files, exported {} files to {}".format(
            self.sent_to_export_files_count,
            len(self.exported_files),
            office_folder))

