from common.snow_ball_file_storage import TSnowBallFileStorage, TSnowBallChecker, TStoredFileParams

import os
import json
from datetime import datetime


class TConvertStorage:

    converted_file_extension = ".pdf.docx"
    converter_id_key = "c"
    broken_stub = b"broken_stub"

    def __init__(self, logger, project_path, user_bin_file_size=None):
        self.logger = logger
        self.main_folder = os.path.dirname(project_path)
        self.project_path = project_path
        with open(self.project_path, "r", encoding="utf8") as inp:
            self.project = json.load(inp)
        self.converted_files_folder = os.path.join(self.main_folder, self.project['converted_folder'])
        self.input_files_folder = os.path.join(self.main_folder, self.project['input_folder'])
        self.access_file_path = self.project.get('access_file_path', os.path.join(self.main_folder, "access.log"))
        self.access_file = open(self.access_file_path, "a+")
        if not os.path.exists(self.input_files_folder):
            os.makedirs(self.input_files_folder)
        if not os.path.exists(self.converted_files_folder):
            os.makedirs(self.converted_files_folder)
        bin_files_size = user_bin_file_size
        if bin_files_size is None:
            bin_files_size =  2 * 2 ** 30
        self.input_file_storage = TSnowBallFileStorage(self.logger, self.input_files_folder,
                                               max_bin_file_size=bin_files_size)
        self.converted_file_storage = TSnowBallFileStorage(self.logger, self.converted_files_folder,
                                                   max_bin_file_size=bin_files_size)
        self.snow_ball_os_error_count = 0

    @staticmethod
    def create_empty_db(input_folder, converted_folder, output_filename):
        db = {
            "input_folder": input_folder,
            "converted_folder": converted_folder
        }
        with open(output_filename, "w") as outf:
            json.dump(db, outf, indent=4)

    def clear_database(self):
        self.input_file_storage.clear_db()
        self.converted_file_storage.clear_db()

    def delete_file_silently(self, full_path):
        try:
            if os.path.exists(full_path):
                self.logger.debug("delete {}".format(full_path))
                os.unlink(full_path)
        except Exception as exp:
            self.logger.error("Exception {}, cannot delete {}, do not know how to deal with it...".format(exp, full_path))

    @staticmethod
    def is_normal_input_file_name(filename):
        file_base_name, extension = os.path.splitext(os.path.basename(filename))
        return len(file_base_name) == 64 and extension == ".pdf"  #len(sha256) == 64

    @staticmethod
    def get_sha256_from_filename(filename):
        filename = os.path.basename(filename)
        e = filename.find(".") # first dot  in "a.pdf.docx"
        if e == -1:
            return None
        sha256 = filename[0:e]
        if len(sha256) != 64:
            return None
        return sha256

    def get_converted_file(self, sha256):
        return self.converted_file_storage.get_saved_file(sha256)

    def has_converted_file(self, sha256):
        return self.converted_file_storage.has_saved_file(sha256)

    def register_access_request(self, sha256, timestamp=None):
        if timestamp is None:
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        else:
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
        self.access_file.write("{}: {}\n".format(time_str, sha256))
        self.access_file.flush()

    def save_converted_file_broken_stub(self, sha256, force=False):
        try:
            self.converted_file_storage.save_file(self.broken_stub, ".docx", None, force=force, sha256=sha256)
        except OSerror:
            self.snow_ball_os_error_count += 1
            raise

    def save_converted_file(self, file_name, sha256, converter_id, force=False, delete_file=True):
        _, file_extension = os.path.splitext(file_name)
        try:
            with open(file_name, "rb") as inp:

                aux_params = json.dumps({self.converter_id_key: converter_id})
                self.converted_file_storage.save_file(inp.read(),
                                                       file_extension,
                                                       aux_params,
                                                       force=force,
                                                       sha256=sha256)
        except OSError:
            self.snow_ball_os_error_count += 1
            raise
        if delete_file:
            self.delete_file_silently(file_name)

    def save_input_file(self, file_name, delete_file=True):
        _, file_extension = os.path.splitext(file_name)
        try:
            with open(file_name, "rb") as inp:
                self.input_file_storage.save_file(inp.read(), file_extension)
        except OSerror:
            self.snow_ball_os_error_count += 1
            raise
        if delete_file:
            self.delete_file_silently(file_name)

    def close_storage(self):
        self.access_file.close()
        self.converted_file_storage.close_file_storage()
        self.input_file_storage.close_file_storage()

    def check_storage(self, file_no=None, fix_file_offset=False):
        files = list()
        if file_no is not None:
            files.append(self.converted_file_storage.get_bin_file_path(file_no))
        else:
            for i in range(len(self.converted_file_storage.bin_files)):
                files.append(self.converted_file_storage.get_bin_file_path(i))
        sha256_list = list()
        doc_params = list()
        for key, value in self.converted_file_storage.get_all_doc_params():
            sha256_list.append(key)
            doc_params.append(TStoredFileParams().read_from_string(value))
        self.logger.info("read {} doc params from {}".format(
            len(doc_params), self.converted_file_storage.header_file_path))
        errors_count = 0
        for file_path in files:
            checker = TSnowBallChecker(self.logger, file_path, doc_params,
                                       broken_stub=TConvertStorage.broken_stub,
                                       file_prefix=b"PK", fix_offset=fix_file_offset)
            errors_count += checker.check_file()
        if fix_file_offset:
            self.converted_file_storage.rewrite_header(sha256_list, doc_params)
        return errors_count
