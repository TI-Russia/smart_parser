import zipfile
import os
import shutil
import logging
from robots.common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_ZIP_EXTENSION, DEFAULT_RAR_EXTENSION, \
    DEFAULT_7Z_EXTENSION
import tempfile

if shutil.which('unrar') is None:
    raise Exception("cannot find unrar (Copyright (c) 1993-2017 Alexander Roshal),\n sudo apt intall unrar")

FILE_EXTENSIONS_IN_ARCHIVE = set()
FILE_EXTENSIONS_IN_ARCHIVE.update(ACCEPTED_DECLARATION_FILE_EXTENSIONS)
FILE_EXTENSIONS_IN_ARCHIVE.add(".htm")
FILE_EXTENSIONS_IN_ARCHIVE.add(".html")


def unzip_one_archive(input_file, main_index, outfolder):
    global FILE_EXTENSIONS_IN_ARCHIVE
    with zipfile.ZipFile(input_file) as zf:
        for archive_index, zipinfo in enumerate(zf.infolist()):
            _, file_extension = os.path.splitext(zipinfo.filename)
            file_extension = file_extension.lower()
            if file_extension not in FILE_EXTENSIONS_IN_ARCHIVE:
                continue
            old_file_name = zipinfo.filename
            zipinfo.filename = "{}_{}{}".format(main_index, archive_index, file_extension)
            zf.extract(zipinfo, path=outfolder)
            yield archive_index, old_file_name, os.path.join(outfolder, zipinfo.filename)


def process_temp_folder(temp_folder, main_index, outfolder):
    global FILE_EXTENSIONS_IN_ARCHIVE
    logger = logging.getLogger("dlrobot_logger")
    for archive_index, filename in enumerate(os.listdir(temp_folder)):
        _, file_extension = os.path.splitext(filename)
        file_extension = file_extension.lower()
        if file_extension not in FILE_EXTENSIONS_IN_ARCHIVE:
            continue
        normalized_file_name = os.path.join(outfolder, "{}_{}{}".format(main_index, archive_index, file_extension))
        try:
            shutil.move(os.path.join(temp_folder, filename), normalized_file_name)
            yield archive_index, filename, normalized_file_name
        except Exception as e:
            logger.error("cannot move file N {} (file name encoding?)".format(archive_index))
    shutil.rmtree(temp_folder)


def unrar_one_archive(input_file, main_index, outfolder):
    logger = logging.getLogger("dlrobot_logger")
    temp_folder = os.path.join(outfolder, "unrar_temp")
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    os.mkdir(temp_folder)
    handle, logfile = tempfile.mkstemp(prefix='unrar')
    os.close(handle)
    cmd = "unrar e -o+ -y {} {} >{}".format(input_file, temp_folder, logfile)
    logger.debug(cmd)
    os.system(cmd)
    for x in process_temp_folder(temp_folder, main_index, outfolder):
        yield x
    os.unlink(logfile)


def un7z_one_archive(input_file, main_index, outfolder):
    logger = logging.getLogger("dlrobot_logger")
    temp_folder = os.path.join(outfolder, "un7z_temp")
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    os.mkdir(temp_folder)
    seven_z_binary = "7z"
    if os.name == "nt":
       seven_z_binary = "C:/cygwin64/lib/p7zip/7z.exe"
    handle, logfile = tempfile.mkstemp(prefix='7zlog')
    os.close(handle)
    cmd = "{} e -bb -y -o{} {} >{}".format(seven_z_binary, temp_folder, input_file.replace("\\", "/"), logfile)
    logger.debug(cmd)
    os.system(cmd)
    os.unlink(logfile)
    for x in process_temp_folder(temp_folder, main_index, outfolder):
        yield x

UNPACKERS = {
    DEFAULT_ZIP_EXTENSION: unzip_one_archive,
    DEFAULT_RAR_EXTENSION: unrar_one_archive,
    DEFAULT_7Z_EXTENSION: un7z_one_archive
}

def is_archive_extension(extension):
    global UNPACKERS
    return extension in UNPACKERS


def dearchive_one_archive(file_extension, input_file, main_index, outfolder):
    global UNPACKERS
    if file_extension in UNPACKERS:
        func = UNPACKERS[file_extension]
    else:
        raise Exception("unknown archive type")
    try:
        for x in func(input_file, main_index, outfolder):
            yield x
    except Exception as exp:
        logger = logging.getLogger("dlrobot_logger")
        logger.error("Exception: {}, cannot unpack {}, keep going...".format(exp, input_file))