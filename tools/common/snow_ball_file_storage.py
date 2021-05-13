from common.primitives import build_dislosures_sha256_by_file_data

import json
import os
import shutil


class TStoredFileParams:
    def __init__(self, bin_file_index=None, file_offset_in_bin_file=None, file_size=None, file_extension=None,
                 aux_params=None):
        self.bin_file_index = bin_file_index
        self.file_offset_in_bin_file = file_offset_in_bin_file
        self.file_size = file_size
        self.file_extension = file_extension
        self.aux_params = aux_params

    def read_from_string(self, value):
        items = value.split(";")
        assert len(items) == 4 or len(items) == 5
        self.bin_file_index, self.file_offset_in_bin_file, self.file_size, self.file_extension = items[0:4]
        self.bin_file_index = int(self.bin_file_index)
        self.file_offset_in_bin_file = int (self.file_offset_in_bin_file)
        self.file_size = int(self.file_size)
        if len(items) == 5:
            self.aux_params = items[4]
        return self

    def to_string(self):
        return "{};{};{};{};{}".format(
            self.bin_file_index,
            self.file_offset_in_bin_file,
            self.file_size,
            self.file_extension,
            self.aux_params)

    def to_json_str(self):
        return json.dumps(self.__dict__)


class TSnowBallFileStorage:
    bin_file_prefix = "fs"
    bin_file_extension = ".bin"
    pdf_cnf_doc_starter = b'<pdf_cnf_doc>'
    pdf_cnf_doc_ender   = b'</pdf_cnf_doc>'
    default_max_bin_file_size = 10 * (2 ** 30)

    def clear_stats(self):
        self.stats = {
            'bin_files_count': 1,
            'all_file_size': 0,
            'source_doc_count': 0
        }

    # disc_sync_rate means that we sync with disk after each sync_period db update
    # disc_sync_rate=1 means sync after each db update
    def __init__(self, logger, data_folder, max_bin_file_size=default_max_bin_file_size):
        self.logger = logger
        self.max_bin_file_size = max_bin_file_size
        self.saved_file_params = dict()
        self.saved_file_params_file = None
        self.data_folder = data_folder
        self.bin_files = list()
        self.header_file_path = os.path.normpath(os.path.join(self.data_folder, "header.dat"))
        self.stats = None
        self.output_bin_file_size = 0
        self.load_from_disk()

    def get_bin_file_path(self, i):
        path = os.path.join(self.data_folder, "{}_{:03d}{}".format(
            self.bin_file_prefix, i, self.bin_file_extension))
        return os.path.normpath(path)

    def looks_like_a_bin_file(self, f):
        return f.startswith(self.bin_file_prefix) and f.endswith(self.bin_file_extension)

    def write_key_to_header(self, key, value):
        self.saved_file_params[key] = value
        self.saved_file_params_file.write("\t".join((key, value)) + "\n")
        self.saved_file_params_file.flush()

    def get_stats_file_path(self):
        return self.header_file_path + ".stats"

    def save_stats(self):
        with open(self.get_stats_file_path(), "w") as outp:
            json.dump(self.stats, outp, indent=4)

    def close_file_storage(self):
        self.save_stats()
        self.saved_file_params_file.close()
        for f in self.bin_files:
            f.close()

    def get_all_doc_params(self):
        self.logger.debug("read snow ball header {} from the beginning".format(self.header_file_path))
        self.saved_file_params_file.seek(0)
        for line in self.saved_file_params_file:
            key, value = line.strip().split("\t")
            yield key, value

    def load_from_disk(self):
        assert os.path.exists(self.data_folder)
        self.saved_file_params_file = open(self.header_file_path, "a+")
        self.saved_file_params = dict(self.get_all_doc_params())

        if os.path.exists(self.get_stats_file_path()):
            with open(self.get_stats_file_path()) as inp:
                self.stats = json.load(inp)
        else:
            self.clear_stats()

        assert (len(self.saved_file_params) == self.stats['source_doc_count'])

        self.bin_files.clear()
        for i in range(self.stats['bin_files_count'] - 1):
            fp = open(self.get_bin_file_path(i), "rb")
            assert fp is not None
            self.bin_files.append(fp)

        last_bin_file_path = self.get_bin_file_path(self.stats['bin_files_count'] - 1)
        if os.path.exists(last_bin_file_path):
            self.output_bin_file_size = os.stat(last_bin_file_path).st_size
            self.logger.debug("open last bin file for writing: {}, file size={}".format(
                last_bin_file_path, self.output_bin_file_size))
        else:
            self.output_bin_file_size = 0
            self.logger.debug("create bin file for writing: {}".format(last_bin_file_path))
        fp = open(last_bin_file_path, "ab+")
        assert fp is not None
        self.bin_files.append(fp)

        file_in_folder = sum(1 for f in os.listdir(self.data_folder) if self.looks_like_a_bin_file(f))
        assert (file_in_folder == self.stats['bin_files_count'])

        self.save_stats()

    def rewrite_header(self, sha256_list, doc_params):
        assert len(sha256_list) == len(self.saved_file_params)
        assert len(sha256_list) == len(doc_params)
        self.saved_file_params_file.close()
        self.saved_file_params_file = open(self.header_file_path, "w")
        self.logger.info("write {} doc_params to {}".format(len(doc_params), self.header_file_path))
        for sha256, header in zip(sha256_list, doc_params):
            self.write_key_to_header(sha256, header.to_string())
        self.saved_file_params_file.close()
        self.saved_file_params_file = open(self.header_file_path, "a+")
        self.saved_file_params = dict(self.get_all_doc_params())

    def clear_db(self):
        self.close_file_storage()

        self.logger.info("rm -rf {}".format(self.data_folder))
        shutil.rmtree(self.data_folder)

        self.logger.info("mkdir {}".format(self.data_folder))
        os.mkdir(self.data_folder)

        self.clear_stats()
        self.save_stats()
        self.load_from_disk()

    def has_saved_file(self, sha256):
        return sha256 in self.saved_file_params

    def get_saved_file(self, sha256):
        file_info = self.saved_file_params.get(sha256)
        if file_info is None:
            self.logger.debug("cannot find key {}".format(sha256))
            return None, None
        params = TStoredFileParams().read_from_string(file_info)
        if params.bin_file_index >= len(self.bin_files):
            self.logger.error("bad file no {} for key ={}  ".format(params.bin_file_index, sha256))
            return None, None
        file_ptr = self.bin_files[params.bin_file_index]
        file_ptr.seek(params.file_offset_in_bin_file)
        file_contents = file_ptr.read(params.file_size)
        return file_contents, params.file_extension

    def create_new_bin_file(self):
        self.bin_files[-1].close()
        self.bin_files[-1] = open(self.get_bin_file_path(len(self.bin_files) - 1), "rb")
        self.bin_files.append(open(self.get_bin_file_path(len(self.bin_files)), "ab+"))
        self.output_bin_file_size = 0

    def write_repeat_header_to_bin_file(self, file_bytes, file_extension, output_bin_file):
        # these headers are needed if the main header is lost
        header_repeat = TSnowBallFileStorage.pdf_cnf_doc_starter + \
            "{};{}".format(len(file_bytes), file_extension).encode('latin') + \
            TSnowBallFileStorage.pdf_cnf_doc_ender
        output_bin_file.write(header_repeat)
        return len(header_repeat)

    def update_stats(self, file_bytes_len):
        self.stats['all_file_size'] += file_bytes_len
        self.stats['source_doc_count'] = len(self.saved_file_params)
        self.stats['bin_files_count'] = len(self.bin_files)
        self.save_stats()

    def save_file(self, file_bytes, file_extension, aux_params=None, force=False, sha256=None):
        if sha256 is None:
            sha256 = build_dislosures_sha256_by_file_data(file_bytes, file_extension)
        if not force and self.saved_file_params.get(sha256) is not None:
            return
        output_bin_file = self.bin_files[-1]
        if self.output_bin_file_size > self.max_bin_file_size:
            self.create_new_bin_file()
            self.save_stats()
            output_bin_file = self.bin_files[-1]
        try:
            bytes_count = self.write_repeat_header_to_bin_file(file_bytes, file_extension, output_bin_file)
            self.output_bin_file_size += bytes_count
        except IOError as exp:
            self.logger.error("cannot write repeat header for {} to {}, exception:{}".format(
                sha256, output_bin_file.name, exp))
            raise
        try:
            start_file_pos = self.output_bin_file_size
            output_bin_file.write(file_bytes)
            output_bin_file.flush()
            self.output_bin_file_size += len(file_bytes)
            assert output_bin_file.tell() == self.output_bin_file_size
        except IOError as exp:
            self.logger.error("cannot write file {}{} (size {}) to {}, exception:{}".format(
                sha256, file_extension, len(file_bytes), output_bin_file.name, exp))
            raise

        try:
            params = TStoredFileParams(
                bin_file_index=len(self.bin_files) - 1,
                file_offset_in_bin_file=start_file_pos,
                file_size=len(file_bytes),
                file_extension=file_extension,
                aux_params=str(aux_params)
            )
            self.write_key_to_header(sha256, params.to_string())
        except Exception as exp:
            self.logger.error("cannot add file info {} to {}, exception:{}".format(
                sha256, self.header_file_path, exp))
            raise

        self.logger.debug("put {}{} (size={}) to bin file {}".format(
            sha256, file_extension, len(file_bytes), len(self.bin_files) - 1))
        self.update_stats(len(file_bytes))

    def get_stats(self):
        return self.stats


class TSnowBallChecker:

    def __init__(self, logger, file_name, doc_params, broken_stub=None, file_prefix=None, fix_offset=False):
        self.logger = logger
        self.file_name = file_name
        self.doc_params = doc_params
        self.broken_stub = broken_stub
        self.canon_file_prefix = file_prefix
        self.file_offset = 0
        self.file_size = os.stat(file_name).st_size
        self.file_ptr = open(file_name, "rb")
        basename = os.path.splitext(os.path.basename(file_name))[0]
        assert basename.startswith("fs_")
        self.bin_file_index = int(basename[3:])
        self.fix_offset = fix_offset

    def read_const(self, canon_str):
        canon_str_len = len(canon_str)
        s = self.file_ptr.read(canon_str_len)
        if s != canon_str:
            raise Exception("bad content at file {} offset {}, must be \"{}\", got \"{}\"".format(
                self.file_name,
                self.file_offset,
                canon_str,
                s))
        self.file_offset += canon_str_len

    def read_till_separator(self, separator=b';'):
        s = b""
        max_count = 15
        while True:
            ch = self.file_ptr.read(1)
            self.file_offset += 1
            if ch == separator:
                break
            s += ch
            if len(s) > max_count:
                raise Exception("cannot find separator \"{}\" at offset {}".format(separator, self.file_offset))
        return s

    def read_bytes(self, bytes_count):
        assert self.file_ptr.tell() == self.file_offset
        s = self.file_ptr.read(bytes_count)
        assert len(s) == bytes_count
        self.file_offset += bytes_count
        return s

    def close(self):
        self.file_ptr.close()

    def check_file(self):
        for file_index in range(len(self.doc_params)):
            if self.doc_params[file_index].bin_file_index == self.bin_file_index:
                break
        errors_count = 0
        try:
            self.logger.info("check {} file_size={}".format(self.file_name, self.file_size))
            doc_index = 0
            while self.file_offset < self.file_size:

                self.read_const(TSnowBallFileStorage.pdf_cnf_doc_starter)
                docx_size = int(self.read_till_separator())
                doc_index += 1
                self.read_const(b'.docx')
                self.read_const(TSnowBallFileStorage.pdf_cnf_doc_ender)
                params = self.doc_params[file_index]
                if params.bin_file_index != self.bin_file_index:
                    errors_count += 1
                    self.logger.error(
                        "params.bin_file_index != r.bin_file_index ({} !={}), doc_index={}, params={}".format(
                            params.bin_file_index, self.bin_file_index, doc_index, params.to_string()
                        ))
                if params.file_offset_in_bin_file != self.file_offset:
                    errors_count += 1
                    self.logger.error(
                        "params.file_offset_in_bin_file != r.file_offset ({} !={}), doc_index={}, params={}".format(
                            params.file_offset_in_bin_file, self.file_offset, doc_index, params.to_string()
                        ))
                    if self.fix_offset:
                        self.logger.error("set file offset to {}".format(self.file_offset))
                        params.file_offset_in_bin_file = self.file_offset

                if params.file_size != docx_size:
                    errors_count += 1
                    self.logger.error(
                        "params.file_size != docx_size ({} !={}), doc_index={}, params={}".format(
                            params.file_size, docx_size, doc_index, params.to_string()
                        ))
                file_index += 1
                file_bytes = self.read_bytes(docx_size)
                comp_prefix = self.canon_file_prefix is None or file_bytes.startswith(self.canon_file_prefix)
                comp_stub = self.broken_stub is None or file_bytes == self.broken_stub
                if not comp_prefix and not comp_stub:
                    errors_count += 1
                    self.logger.error(
                        "file must start with prefix {}, it starts with {}, doc_index={}, params={} ".format(
                            self.canon_file_prefix,
                            file_bytes[0:len(self.canon_file_prefix)],
                            doc_index,
                            params.to_string()
                        ))
            return errors_count
        finally:
            self.close()
