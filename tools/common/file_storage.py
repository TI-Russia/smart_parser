import hashlib
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

    def get_bin_file_path(self, i):
        return os.path.join(self.data_folder, "{}.bin".format(i))

    def __init__(self, logger, data_folder, max_bin_file_size=default_max_bin_file_size):
        self.data_folder =  data_folder
        self.max_bin_file_size = max_bin_file_size
        self.logger = logger
        self.stats = None
        self.saved_file_params = None
        self.bin_files = list()
        self.dbm_path = None
        self.load_from_disk()
        self.sync_after_write = (os.name == "nt")

    def write_key_to_dbm(self, key, value):
        self.saved_file_params[key] = value
        if self.sync_after_write:
            self.saved_file_params.sync()

    def open_dbm(self):
        if os.path.exists(self.dbm_path):
            open_mode = "w"
        else:
            open_mode = "c"
        if os.name != "nt":
            open_mode += "s"
        self.logger.info("open gdb file {} with mode: {}".format(self.dbm_path, open_mode))
        self.saved_file_params = gdbm.open(self.dbm_path, open_mode)
        if open_mode[0] == "w":
            self.stats = json.loads(self.saved_file_params.get('stats'))

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

        fp = open(self.get_bin_file_path(self.stats['bin_files_count'] - 1), "ab+")
        assert fp is not None
        self.bin_files.append(fp)

    def clear_db(self):
        self.close_file_storage()

        self.logger("rm -rf self.data_folder")
        shutil.rmtree(self.data_folder, ignore_errors=True)

        self.logger("mkdir self.data_folder")
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
        if len(file_info) == 5:
            aux_params = file_info[4] # not used, but saved for the future
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
        self.write_key_to_dbm("stats", json.dumps(self.stats))

    def save_file(self, file_bytes, file_extension, aux_params=None, force=False, sha256=None):
        if sha256 is None:
            sha256 = hashlib.sha256(file_bytes).hexdigest()
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
            self.saved_file_params.close()
            self.bin_files[-1].close()