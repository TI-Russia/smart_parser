from common.primitives import build_dislosures_sha256_by_file_data

import json
import os
if os.name != "nt":
    # not supported on widows
    import dbm.gnu as gdbm
else:
    import dbm.dumb as gdbm

import os
import shutil

default_max_bin_file_size = 10 * (2 ** 30)


class TFileStorage:
    header_repeat_max_len = 20
    stats_key = "stats"

    def get_bin_file_path(self, i):
        return os.path.join(self.data_folder, "{}.bin".format(i))

    # disc_sync_rate means that we sync with disk after each sync_period db update
    # disc_sync_rate=1 means sync after each db update
    def __init__(self, logger, data_folder, max_bin_file_size=default_max_bin_file_size, disc_sync_rate=1, read_only=False):
        self.data_folder =  data_folder
        self.read_only = read_only
        self.max_bin_file_size = max_bin_file_size
        self.logger = logger
        self.stats = None
        self.saved_file_params = None
        self.bin_files = list()
        self.dbm_path = None
        self.load_from_disk()
        self.write_without_sync_count = 0
        if os.name == "nt":
            self.disc_sync_rate = disc_sync_rate
        else:
            self.disc_sync_rate = None

    def write_key_to_dbm(self, key, value):
        self.saved_file_params[key] = value
        self.write_without_sync_count += 1

        if self.disc_sync_rate is not None and self.write_without_sync_count >= self.disc_sync_rate:
            if self.disc_sync_rate > 1:
                self.logger.debug("sync db")
            self.saved_file_params.sync()
            self.write_without_sync_count = 0

    def get_all_keys(self):
        k = self.saved_file_params.firstkey()
        while k is not None:
            key = k.decode('latin')
            if key != TFileStorage.stats_key:
                yield key
            k = self.saved_file_params.nextkey(k)

    def open_dbm(self):
        if self.read_only:
            open_mode = "r"
        else:
            if os.path.exists(self.dbm_path):
                open_mode = "w"
            else:
                open_mode = "c"
            if os.name != "nt":
                open_mode += "s"
        self.logger.info("open dbm file {} with mode: {}".format(self.dbm_path, open_mode))
        self.saved_file_params = gdbm.open(self.dbm_path, open_mode)
        if open_mode[0] == "w" or open_mode[0] == "r":
            self.stats = json.loads(self.saved_file_params.get(TFileStorage.stats_key))

    def load_from_disk(self):
        self.stats = {
            'bin_files_count': 1,
            'all_file_size': 0,
            'source_doc_count': 0
        }
        assert os.path.exists(self.data_folder)
        self.dbm_path = os.path.join(self.data_folder, "header.dbm")
        self.open_dbm()

        self.bin_files.clear()
        for i in range(self.stats['bin_files_count'] - 1):
            fp = open(self.get_bin_file_path(i), "rb")
            assert fp is not None
            self.bin_files.append(fp)

        last_file_mode = "ab+" if not self.read_only else "rb"
        last_fp = open(self.get_bin_file_path(self.stats['bin_files_count'] - 1), last_file_mode)
        assert last_fp is not None
        self.bin_files.append(last_fp)

    def clear_db(self):
        self.close_file_storage()

        self.logger.info("rm -rf {}".format(self.data_folder))
        shutil.rmtree(self.data_folder)

        self.logger.info("mkdir {}".format(self.data_folder))
        os.mkdir(self.data_folder)

        self.load_from_disk()

    def has_saved_file(self, sha256):
        return sha256 in self.saved_file_params

    def get_saved_file(self, sha256):
        file_info = self.saved_file_params.get(sha256)
        if file_info is None:
            self.logger.debug("cannot find key {}".format(sha256))
            return None, None
        file_info = file_info.decode('latin').split(";")
        file_no, file_pos, size, extension = file_info[0:4]
        file_no = int(file_no)
        if file_no >= len(self.bin_files):
            self.logger.error("bad file no {} for key ={}  ".format(file_no, sha256))
            return None, None
        self.bin_files[file_no].seek(int(file_pos))
        file_contents = self.bin_files[file_no].read(int(size))
        return file_contents, extension

    def create_new_bin_file(self):
        self.bin_files[-1].close()
        self.bin_files[-1] = open(self.get_bin_file_path(len(self.bin_files) - 1), "rb")

        self.bin_files.append (open(self.get_bin_file_path(len(self.bin_files)), "ab+"))

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
        self.stats['bin_files_count'] = len(self.bin_files)
        self.write_key_to_dbm(TFileStorage.stats_key, json.dumps(self.stats))

    def save_file(self, file_bytes, file_extension, aux_params=None, force=False, sha256=None):
        if self.read_only:
            self.logger.error("cannot save file since the db is opened in read-only mode")
            return
        if sha256 is None:
            sha256 = build_dislosures_sha256_by_file_data(file_bytes, file_extension)
        if not force and self.saved_file_params.get(sha256) is not None:
            return
        output_bin_file = self.bin_files[-1]
        if output_bin_file.tell() > self.max_bin_file_size:
            self.create_new_bin_file()
            output_bin_file = self.bin_files[-1]
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
            self.logger.error("cannot write file {}{} (size {}) to {}, exception:{}".format(
                sha256, file_extension, len(file_bytes), output_bin_file.name, exp))
            raise

        try:
            value = "{};{};{};{};{}".format(
                len(self.bin_files) - 1,
                start_file_pos,
                len(file_bytes),
                file_extension,
                aux_params)
            self.write_key_to_dbm(sha256, value)
        except Exception as exp:
            self.logger.error("cannot add file info {} to {}, exception:{}".format(
                sha256, self.dbm_path, exp))
            raise

        self.logger.debug("put {}{} (size={}) to bin file {}".format(
            sha256, file_extension, len(file_bytes), len(self.bin_files) - 1 ))
        self.update_stats(len(file_bytes))

    def get_stats(self):
        return self.stats

    def close_file_storage(self):
        if self.saved_file_params is not None:
            if not self.read_only:
                self.saved_file_params.sync() # for nt
            self.saved_file_params.close()
            self.bin_files[-1].close()

    def check_storage(self, fail_fast):
        i = 0
        errors_count  = 0
        for key in self.get_all_keys():
            i += 1
            if (i % 100) == 0:
                self.logger.debug("file N {}".format(i))
            data, file_extension = self.get_saved_file(key)
            sha256 = build_dislosures_sha256_by_file_data(data, file_extension)
            if sha256 != key:
                errors_count += 1
                self.logger.error("key {} has invalid data, length={}, file_extension={}".format(
                    key, len(data), file_extension))
                if fail_fast:
                    self.logger.error("stop checking")
                    return False
        self.logger.info("checked {} documents, errors_count={}".format(i, errors_count))
        return errors_count == 0
