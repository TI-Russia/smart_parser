import zipfile
import os
import shutil
import logging
from content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_ZIP_EXTENSION, DEFAULT_RAR_EXTENSION, \
    DEFAULT_7Z_EXTENSION


def unzip_one_archive(input_file, main_index, outfolder):
    with zipfile.ZipFile(input_file) as zf:
        for archive_index, zipinfo in enumerate(zf.infolist()):
            _, file_extension = os.path.splitext(zipinfo.filename)
            file_extension = file_extension.lower()
            if file_extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
                continue
            old_file_name = zipinfo.filename
            zipinfo.filename = os.path.join(outfolder, "{}_{}{}".format(main_index, archive_index, file_extension))
            zf.extract(zipinfo)
            yield archive_index, old_file_name, zipinfo.filename


def process_temp_folder(temp_folder, main_index, outfolder):
    logger = logging.getLogger("dlrobot_logger")
    for archive_index, filename in enumerate(os.listdir(temp_folder)):
        _, file_extension = os.path.splitext(filename)
        file_extension = file_extension.lower()
        if file_extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
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
    cmd = "unrar e {} {} >unrar.log".format(input_file, temp_folder)
    logger.debug(cmd)
    os.system(cmd)
    os.unlink("unrar.log")
    for x in process_temp_folder(temp_folder, main_index, outfolder):
        yield x


def un7z_one_archive(input_file, main_index, outfolder):
    logger = logging.getLogger("dlrobot_logger")
    temp_folder = os.path.join(outfolder, "un7z_temp")
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    os.mkdir(temp_folder)
    seven_z_binary = "7z"
    if os.name == "nt":
       seven_z_binary = "C:/cygwin64/lib/p7zip/7z.exe"
    cmd = "{} e -bb -y -o{} {} >7z.log".format(seven_z_binary, temp_folder, input_file.replace("\\", "/"))
    logger.debug(cmd)
    os.system(cmd)
    os.unlink("7z.log")
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