import hashlib
import json
import dbm.gnu
import os

default_max_bin_file_size = 10 * (2 ** 30)


class TFileStorage:
    header_repeat_max_len = 20

    def get_bin_file_path(self, i):
        return os.path.join(self.data_folder, "{}.bin".format(i))

    def __init__(self, logger, data_folder, max_bin_file_size=default_max_bin_file_size):
        self.data_folder =  data_folder
        self.max_bin_file_size = max_bin_file_size
        self.logger = logger
        self.stats = None
        self.saved_file_params = None
        self.files = list()
        self.dbm_path = None
        self.load_from_disk()

    def load_from_disk(self):
        self.stats = {
            'bin_files_count': 1,
            'all_file_size': 0,
            'source_doc_count': 0
        }
        assert os.path.exists(self.data_folder)
        self.dbm_path = os.path.join(self.data_folder, "header.dbm")
        if os.path.exists(self.dbm_path):
            self.saved_file_params = dbm.gnu.open(self.dbm_path, "ws")
            self.stats = json.loads(self.saved_file_params.get('stats'))
        else:
            self.logger.info("create new file {}".format(self.dbm_path))
            self.saved_file_params = dbm.gnu.open(self.dbm_path, "cs")

        self.files.clear()
        for i in range(self.stats['bin_files_count'] - 1):
            fp = open(self.get_bin_file_path(i), "rb")
            assert fp is not None
            self.files.append(fp)

        fp = open(self.get_bin_file_path(self.stats['bin_files_count'] - 1), "ab+")
        assert fp is not None
        self.files.append(fp)

    def close_files(self):
        for f in self.files:
            self.logger.debug("close {}".format(f.name))
            f.close()
        self.files.clear()
        self.saved_file_params.close()

    def get_saved_file(self, sha256):
        file_info = self.saved_file_params.get(sha256)
        if file_info is None:
            self.logger.debug("cannot find key {}".format(sha256))
            return None, None
        file_no, file_pos, size, extension = file_info.decode('latin').split(";")
        file_no = int(file_no)
        if file_no >= len(self.files):
            self.logger.error("bad file no {} for key ={}  ".format(file_no, sha256))
            return None, None
        self.files[file_no].seek(int(file_pos))
        file_contents = self.files[file_no].read(int(size))
        return file_contents, extension

    def create_new_bin_file(self):
        self.files[-1].close()
        self.files[-1] = open(self.get_bin_file_path(len(self.files) - 1), "rb")

        self.files.append (open(self.get_bin_file_path(len(self.files)), "ab+"))

    def write_repeat_header_to_bin_file(self, file_bytes, file_extension, output_bin_file):
        # these headers are needed if the main dbm is lost
        header_repeat = '{};{}'.format(len(file_bytes), file_extension)
        if len(header_repeat) > self.header_repeat_max_len:
            # strange long file extension can be ignored and trimmed
            header_repeat = header_repeat[:self.header_repeat_max_len]
        elif len(header_repeat) > self.header_repeat_max_len:
            header_repeat += ' ' * (self.header_repeat_max_len - len(header_repeat))
        output_bin_file.write(header_repeat.encode('latin'))

    def update_stats(self, file_bytes_len):
        self.stats['all_file_size'] += file_bytes_len + self.header_repeat_max_len
        self.stats['source_doc_count'] += 1
        self.stats['bin_files_count'] = len(self.files)
        self.saved_file_params["stats"] = json.dumps(self.stats)

    def save_file(self, file_bytes, file_extension):
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        if self.saved_file_params.get(sha256) is not None:
            return
        output_bin_file = self.files[-1]
        if output_bin_file.tell() > self.max_bin_file_size:
            self.create_new_bin_file()
            output_bin_file = self.files[-1]
        try:
            self.write_repeat_header_to_bin_file(file_bytes, file_extension, output_bin_file)
        except IOError as exp:
            self.logger.error("cannot write repeat header for {} to {}, exception:{}".format(
                sha256, output_bin_file.name, exp))
            raise
        try:
            start_file_pos = output_bin_file.tell()
            output_bin_file.write(file_bytes)
            output_bin_file.flush()
        except IOError as exp:
            self.logger.error("cannot write file {} (size {}) to {}, exception:{}".format(
                sha256, file_bytes, output_bin_file.name, exp))
            raise

        try:
            self.saved_file_params[sha256] = "{};{};{};{}".format(
                len(self.files) - 1,
                start_file_pos,
                len(file_bytes),
                file_extension)
        except Exception as exp:
            self.logger.error("cannot add file info {} to {}, exception:{}".format(
                sha256, self.dbm_path, exp))
            raise

        self.logger.debug("put source document {} to bin file {}".format(sha256, len(self.files) - 1 ))
        self.update_stats(len(file_bytes))

    def get_stats(self):
        return self.stats
