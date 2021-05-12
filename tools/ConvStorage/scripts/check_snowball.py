from common.logging_wrapper import setup_logging
from common.snow_ball_file_storage import TSnowBallFileStorage, TStoredFileParams
from ConvStorage.convert_storage import TConvertStorage
import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin-folder", dest='bin_folder')
    parser.add_argument("--file-path", dest='file_path')
    return parser.parse_args()


class TFileReader:

    def __init__(self, file_name):
        self.file_name = file_name
        self.file_offset = 0
        self.file_size = os.stat(file_name).st_size
        self.file_ptr = open(file_name, "rb")
        basename = os.path.splitext(os.path.basename(file_name))[0]
        print (basename)
        assert basename.startswith("fs_")
        self.bin_file_index = int(basename[3:])

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


def check_file(logger, file_path, doc_params):
    r = TFileReader(file_path)

    for file_index in range(len(doc_params)):
        if doc_params[file_index].bin_file_index == r.bin_file_index:
            break
    try:
        logger.info("check {} file_size={}".format(r.file_name, r.file_size))
        doc_index = 0
        while r.file_offset < r.file_size:

            r.read_const(b'<pdf_cnf_doc>')
            docx_size = int(r.read_till_separator())
            doc_index += 1
            r.read_const(b'.docx')
            r.read_const(b'</pdf_cnf_doc>')
            params = doc_params[file_index]
            if  params.bin_file_index != r.bin_file_index:
                logger.error(
                    "params.bin_file_index != r.bin_file_index ({} !={}), doc_index={}, params={}".format(
                        params.bin_file_index, r.bin_file_index, doc_index, params.to_string()
                    ))
            if params.file_offset_in_bin_file != r.file_offset:
                logger.error(
                    "params.file_offset_in_bin_file != r.file_offset ({} !={}), doc_index={}, params={}".format(
                        params.file_offset_in_bin_file, r.file_offset, doc_index, params.to_string()
                    ))
            if params.file_size != docx_size:
                logger.error(
                    "params.file_size != docx_size ({} !={}), doc_index={}, params={}".format(
                        params.file_size, docx_size, doc_index, params.to_string()
                    ))
            file_index += 1
            docx_bytes = r.read_bytes(docx_size)
            if docx_size != len(TConvertStorage.broken_stub) or TConvertStorage.broken_stub != docx_bytes:
                if docx_bytes[0:2] != b"PK":
                    logger.error("docx must start with prefix b'PK', it starts with {}, doc_index={}, params={} ".format(
                        doc_index, docx_bytes[0:2], doc_index, params.to_string()
                    ))
    finally:
        r.close()


if __name__ == '__main__':
    args = parse_args()
    logger = setup_logging(log_file_name="check_snowball.log")
    folder = args.bin_folder
    if folder is None:
        folder = os.path.dirname(args.file_path)
    doc_params = list()
    with open(os.path.join(folder, "header.dat"), "r") as inp:
        for line in inp:
            key, value = line.strip().split("\t")
            params = TStoredFileParams().read_from_string(value)
            doc_params.append(params)
    logger.info("read {} doc params".format(len(doc_params)))

    if args.bin_folder is not None:
        logger.info("list files in folder {}".format(args.bin_folder))
        for file_name in os.listdir(args.bin_folder):
            if file_name.startswith("fs_") and file_name.endswith(".bin"):
                check_file(logger, os.path.join(args.bin_folder, file_name), doc_params)
    else:
        assert args.file_path is not None
        check_file(logger, args.file_path, doc_params)
