import os
import json
import shutil
import time
import threading


def move_file_with_retry(logger, file_name, folder):
    for try_index in [1, 2, 3]:
        try:
            shutil.move(file_name, folder)
            return
        except Exception as exp:
            logger.error("cannot move {}, exception={}, wait 20 seconds...".format(file_name, exp))
            time.sleep(20)
    shutil.move(file_name, folder)


class TConvertStorage:

    converted_file_extension = ".pdf.docx"

    def __init__(self, logger, conv_db_json_file_name, new_db=False):
        self.logger = logger
        self.conv_db_json_file_name = conv_db_json_file_name
        self.conv_db_json = None
        with open(self.conv_db_json_file_name, "r", encoding="utf8") as inp:
            self.conv_db_json = json.load(inp)
        self.converted_files_folder = self.conv_db_json['converted_folder']
        self.input_files_folder = self.conv_db_json['input_folder']
        if not os.path.exists(self.input_files_folder):
            os.makedirs(self.input_files_folder)
        if not os.path.exists(self.converted_files_folder):
            os.makedirs(self.converted_files_folder)
        self.modify_json_lock = threading.Lock()
        assert "files" in self.conv_db_json
        self.last_save_time = time.time()

    @staticmethod
    def create_empty_db(output_filename, input_folder, converted_folder):
        db = {
            "files": {},
            "input_folder": input_folder,
            "converted_folder": converted_folder
        }
        with open(output_filename, "w") as outf:
            json.dump(db, outf, indent=4)

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

    def clear_database(self):
        self.conv_db_json['files'] = dict()
        self.save_database()

    def save_database(self):
        self.modify_json_lock.acquire()
        try:
            with open(self.conv_db_json_file_name, "w") as outf:
                json.dump(self.conv_db_json, outf, indent=4)
            self.last_save_time = time.time()
        finally:
            self.modify_json_lock.release()

    def recreate_database(self):
        for f in os.listdir(os.path.join(self.converted_files_folder)):
            if not f.endswith(self.converted_file_extension):
                self.logger.error("bad file name {}".format(f))
                assert f.endswith(self.converted_file_extension)
            sha256 = f[:-len(self.converted_file_extension)]
            self.conv_db_json['files'][sha256] = {}

    def get_converted_file_name(self, sha256):
        return os.path.join(self.converted_files_folder, sha256 + self.converted_file_extension)

    def has_converted_file(self, sha256):
        filename = self.get_converted_file_name(sha256)
        if filename is None:
            return False
        return os.path.exists(filename)

    def register_access_request(self, sha256):
        file_info = self.conv_db_json['files'].get(sha256)
        if file_info is None:
            return
        file_info['a'] = int(time.time()/(60*60*24))  # in days

    def save_converted_file(self, file_name, sha256, converter_id):
        converted_file = self.get_converted_file_name(sha256)
        self.logger.debug("move {} to {}".format(file_name, converted_file))
        move_file_with_retry(self.logger, file_name, converted_file)

        self.modify_json_lock.acquire()
        try:
            self.conv_db_json['files'][sha256] = {"c": converter_id}
        finally:
            self.modify_json_lock.release()

    def get_input_file_name(self, sha256):
        return os.path.join(self.input_files_folder, sha256 + ".pdf")

    def save_input_file(self, file_name, sha256):
        input_file = self.get_input_file_name(sha256)
        self.logger.debug("move {} to {}".format(file_name, input_file))
        move_file_with_retry(self.logger, file_name, input_file)

    def delete_conversion_record(self, sha256):
        if sha256 not in self.conv_db_json['files']:
            return False
        self.logger.debug("delete_conversion_record {}".format(sha256))
        file_path = self.get_converted_file_name(sha256)
        if os.path.exists(file_path):
            self.logger.debug("delete {}".format(file_path))
            os.remove(file_path)

        file_path = self.get_input_file_name(sha256)
        if os.path.exists(file_path):
            self.logger.debug("delete {}".format(file_path))
            os.remove(file_path)

        self.modify_json_lock.acquire()
        try:
            del self.conv_db_json['files'][sha256]
        finally:
            self.modify_json_lock.release()
        self.save_database()
        return True
