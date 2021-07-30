from common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_ZIP_EXTENSION, DEFAULT_RAR_EXTENSION, \
    DEFAULT_7Z_EXTENSION

import zipfile
import os
import shutil


if shutil.which('unrar') is None:
    raise Exception("cannot find unrar (Copyright (c) 1993-2017 Alexander Roshal),\n sudo apt install unrar")

FILE_EXTENSIONS_IN_ARCHIVE = set()
FILE_EXTENSIONS_IN_ARCHIVE.update(ACCEPTED_DECLARATION_FILE_EXTENSIONS)
FILE_EXTENSIONS_IN_ARCHIVE.add(".htm")
FILE_EXTENSIONS_IN_ARCHIVE.add(".html")


class TDearchiver:
    def __init__(self, logger, outfolder):
        self.outfolder = outfolder
        self.logger = logger
        if not os.path.exists(self.outfolder):
            self.logger.error("export folder {} must exist before calling TDearchiver".format(outfolder))
            os.makedirs(self.outfolder, exist_ok=True)


    def unzip_one_archive(self, input_file, main_index):
        global FILE_EXTENSIONS_IN_ARCHIVE
        with zipfile.ZipFile(input_file) as zf:
            for archive_index, zipinfo in enumerate(zf.infolist()):
                _, file_extension = os.path.splitext(zipinfo.filename)
                file_extension = file_extension.lower()
                if file_extension not in FILE_EXTENSIONS_IN_ARCHIVE:
                    continue
                old_file_name = zipinfo.filename
                zipinfo.filename = "{}_{}{}".format(main_index, archive_index, file_extension)
                zf.extract(zipinfo, path=self.outfolder)
                yield archive_index, old_file_name, os.path.join(self.outfolder, zipinfo.filename)

    def _dearchive_one_archive_template(self, input_file, main_index, dearchive_template_str):
        input_file = os.path.abspath(input_file)
        temp_folder = os.path.abspath(os.path.join(self.outfolder, "dearchive_temp"))
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
        os.makedirs(temp_folder, exist_ok=True)
        log_path = "log.log"
        cmd = "cd {}; {} {} > {}".format(temp_folder, dearchive_template_str, input_file, log_path)
        self.logger.debug(cmd)
        os.system(cmd)

        archive_files = os.listdir(temp_folder)
        if len(archive_files) == 1:  #only log file
            log_file_path = os.path.join(temp_folder, log_path)
            try:
                with open(log_file_path) as inp:
                    log_contents = inp.read()
                self.logger.error(log_contents.replace("\n", " "))
            except Exception as exp:
                pass

        cnt = 0
        for archive_index, filename in enumerate(archive_files):
            _, file_extension = os.path.splitext(filename)
            file_extension = file_extension.lower()
            if file_extension not in FILE_EXTENSIONS_IN_ARCHIVE:
                continue
            normalized_file_name = os.path.join(self.outfolder, "{}_{}{}".format(main_index, archive_index, file_extension))
            try:
                shutil.move(os.path.join(temp_folder, filename), normalized_file_name)
                cnt += 1
                yield archive_index, filename, normalized_file_name
            except Exception as e:
                self.logger.error("cannot move file N {} (file name encoding?)".format(archive_index))
        shutil.rmtree(temp_folder)

        self.logger.debug("extracted {} files from {}".format(cnt, input_file))

    def unrar_one_archive(self, input_file, main_index):
        for x in self._dearchive_one_archive_template(input_file, main_index, "unrar e -o+ -y"):
            yield x

    def un7z_one_archive(self, input_file, main_index):
        if os.name == "nt":
            cmd = 'C:/cygwin64/lib/p7zip/7z.exe e -bb -y'
        else:
            cmd = '7z e -bb -y'
        for x in self._dearchive_one_archive_template(input_file.replace("\\", "/"), main_index, cmd):
            yield x

    @staticmethod
    def is_archive_extension(extension):
        return extension in {DEFAULT_ZIP_EXTENSION, DEFAULT_RAR_EXTENSION, DEFAULT_7Z_EXTENSION}

    def dearchive_one_archive(self, file_extension, input_file, main_index):
        assert self.is_archive_extension(file_extension)
        if file_extension == DEFAULT_ZIP_EXTENSION:
            func = self.unzip_one_archive
        elif file_extension == DEFAULT_RAR_EXTENSION:
            func = self.unrar_one_archive
        elif file_extension == DEFAULT_7Z_EXTENSION:
            func = self.un7z_one_archive
        else:
            raise Exception("unknown archive type")

        try:
            for x in func(input_file, main_index):
                yield x
        except Exception as exp:
            self.logger.error("Exception: {}, cannot unpack {}, keep going...".format(exp, input_file))