import time
import http.client
import logging
import urllib
import threading
import hashlib
import os
from robots.common.archives import dearchive_one_archive, is_archive_extension
from robots.common.content_types import DEFAULT_PDF_EXTENSION
from tempfile import TemporaryDirectory

DECLARATOR_CONV_URL = os.environ.get('DECLARATOR_CONV_URL')
if DECLARATOR_CONV_URL is None:
    print("specify environment variable DECLARATOR_CONV_URL to obtain docx by pdf-files")
    assert DECLARATOR_CONV_URL is not None


def assert_declarator_conv_alive():
    global DECLARATOR_CONV_URL
    if DECLARATOR_CONV_URL is None:
        raise Exception("environment variable DECLARATOR_CONV_URL is not set")

    try:
        with urllib.request.urlopen("http://" + DECLARATOR_CONV_URL+"/ping") as response:
            if response.read() == "yes":
                return True
    except Exception as exp:
        print("cannot connect to {} (declarator conversion server)".format(DECLARATOR_CONV_URL))
        raise


def process_files_to_convert_in_another_thread(conversion_tasks):
    while True:
        time.sleep(5)
        files = conversion_tasks.pop_files()
        if len(files) == 0 and not conversion_tasks.wait_new_tasks:
            break

        for filename, file_extension in files:
            if is_archive_extension(file_extension):
                with TemporaryDirectory(prefix="conversion_folder", dir=".") as tmp_folder:
                    for archive_index, name_in_archive, export_filename in dearchive_one_archive(file_extension, filename, 0, tmp_folder):
                        if export_filename.endswith(DEFAULT_PDF_EXTENSION):
                            conversion_tasks.send_file_to_conversion_db(export_filename, DEFAULT_PDF_EXTENSION)
            else:
                conversion_tasks.send_file_to_conversion_db(filename, file_extension)


class TConversionTasks(object):
    def __init__(self):
        global DECLARATOR_CONV_URL
        self.wait_new_tasks = True
        self._files = list()
        self._sent_tasks = list()
        self.lock = threading.Lock()
        self.conversion_thread = threading.Thread(target=process_files_to_convert_in_another_thread, args=(self,))
        self.db_conv_url = DECLARATOR_CONV_URL
        self.logger = logging.getLogger("dlrobot_logger")

    def check_file_was_converted(self, sha256):
        conn = http.client.HTTPConnection(self.db_conv_url)
        conn.request("GET", "?download_converted_file=0&sha256=" + sha256)
        return conn.getresponse().code == 200

    def retrieve_document(self, sha256, output_file_name):
        conn = http.client.HTTPConnection(self.db_conv_url)
        conn.request("GET", "?sha256=" + sha256)
        response = conn.getresponse()
        if response.code == 200:
            with open(output_file_name, "wb") as out:
                out.write(response.read())
            return True
        else:
            return False

    def start_thread(self):
        self.conversion_thread.start()

    def add_file(self, file, file_extension):
        self.lock.acquire()
        try:
            self._files.append((file, file_extension))
        finally:
            self.lock.release()

    def register_task(self, file_extension, file_contents, sha256):
        conn = http.client.HTTPConnection(self.db_conv_url)
        conn.request("PUT", "/file" + file_extension, file_contents)
        response = conn.getresponse()
        if response.code != 201:
            self.logger.error("could not put a task to conversion queue")
        else:
            self.lock.acquire()
            try:
                self._sent_tasks.append(sha256)
            finally:
                self.lock.release()

    def send_file_to_conversion_db(self, filename, file_extension):
        try:
            with open(filename, "rb") as f:
                file_contents = f.read()
                hashcode = hashlib.sha256(file_contents).hexdigest()

            if hashcode in self._sent_tasks:
                return
            if self.check_file_was_converted(hashcode):
                return
            self.logger.debug("register conversion task for {}".format(filename))
            self.register_task(file_extension, file_contents, hashcode)
        except Exception as exp:
            self.logger.error("cannot process {}: {}".format(filename, exp))

    def pop_files(self):
        result = list()
        self.lock.acquire()
        try:
            result = list(self._files)
            self._files.clear()
        finally:
            self.lock.release()
        return result

    def wait_conversion_tasks(self, timeout_in_seconds=60*30):
        start_time = time.time()
        while len(self._sent_tasks) > 0:
            time.sleep(10)
            for sha256 in list(self._sent_tasks):
                if self.check_file_was_converted(sha256):
                    self._sent_tasks.remove(sha256)
            if time.time() > start_time + timeout_in_seconds:
                self.logger.error("timeout exit, {} conversion tasks were not completed".format(len(self._sent_tasks)))
                break


CONVERSION_TASKS = None


def start_conversion_task_if_needed(filename, file_extension):
    global CONVERSION_TASKS
    if CONVERSION_TASKS is None:
        CONVERSION_TASKS = TConversionTasks()
        CONVERSION_TASKS.start_thread()

    if file_extension == DEFAULT_PDF_EXTENSION or is_archive_extension(file_extension):
        CONVERSION_TASKS.add_file(filename, file_extension)


def wait_doc_conversion_finished():
    global CONVERSION_TASKS
    if CONVERSION_TASKS is not None:
        try:
            CONVERSION_TASKS.wait_new_tasks = False
            CONVERSION_TASKS.conversion_thread.join()
            CONVERSION_TASKS.wait_conversion_tasks()
            CONVERSION_TASKS = None
        except Exception as exp:
            logging.getLogger("dlrobot_logger").error("wait_doc_conversion_finished, exception caught: {}".format(exp))

def stop_conversion_thread():
    global CONVERSION_TASKS
    if CONVERSION_TASKS is not None:
        CONVERSION_TASKS.conversion_thread.join()
        CONVERSION_TASKS = None