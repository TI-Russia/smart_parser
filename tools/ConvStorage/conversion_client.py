import time
import http.client
import logging
import urllib.request
import urllib.error
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


class TDocConversionClient(object):
    def __init__(self):
        global DECLARATOR_CONV_URL
        assert_declarator_conv_alive()
        self.wait_new_tasks = True
        self._files = list()
        self._sent_tasks = list()
        self.lock = threading.Lock()
        self.conversion_thread = None
        self.db_conv_url = DECLARATOR_CONV_URL
        self.logger = logging.getLogger("dlrobot_logger")

    def start_conversion_thread(self):
        self.conversion_thread = threading.Thread(target=self._process_files_to_convert_in_a_separate_thread, args=())
        self.conversion_thread.start()

    def _process_files_to_convert_in_a_separate_thread(self):
        while True:
            time.sleep(5)
            files = self._pop_files()
            if len(files) == 0 and not self.wait_new_tasks:
                break

            for filename, file_extension in files:
                if is_archive_extension(file_extension):
                    with TemporaryDirectory(prefix="conversion_folder", dir=".") as tmp_folder:
                        for archive_index, name_in_archive, export_filename in dearchive_one_archive(file_extension,
                                                                                                     filename, 0,
                                                                                                     tmp_folder):
                            if export_filename.endswith(DEFAULT_PDF_EXTENSION):
                                self._send_file_to_conversion_db(export_filename, DEFAULT_PDF_EXTENSION)
                else:
                    self._send_file_to_conversion_db(filename, file_extension)

    def _add_file(self, file, file_extension):
        self.lock.acquire()
        try:
            self._files.append((file, file_extension))
        finally:
            self.lock.release()

    def _register_task(self, file_extension, file_contents, sha256):
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

    def _send_file_to_conversion_db(self, filename, file_extension):
        try:
            with open(filename, "rb") as f:
                file_contents = f.read()
                hashcode = hashlib.sha256(file_contents).hexdigest()

            if hashcode in self._sent_tasks:
                return
            if self.check_file_was_converted(hashcode):
                return
            self.logger.debug("register conversion task for {}".format(filename))
            self._register_task(file_extension, file_contents, hashcode)
        except Exception as exp:
            self.logger.error("cannot process {}: {}".format(filename, exp))

    def _pop_files(self):
        result = list()
        self.lock.acquire()
        try:
            result = list(self._files)
            self._files.clear()
        finally:
            self.lock.release()
        return result

    def _wait_conversion_tasks(self, timeout_in_seconds=60*30):
        start_time = time.time()
        while len(self._sent_tasks) > 0:
            time.sleep(10)
            for sha256 in list(self._sent_tasks):
                if self.check_file_was_converted(sha256):
                    self._sent_tasks.remove(sha256)
            if time.time() > start_time + timeout_in_seconds:
                self.logger.error("timeout exit, {} conversion tasks were not completed".format(len(self._sent_tasks)))
                break

    def stop_conversion_thread(self):
        self._files = []
        self.wait_new_tasks = False
        self.conversion_thread.join()

    def check_file_was_converted(self, sha256):
        conn = http.client.HTTPConnection(self.db_conv_url)
        conn.request("GET", "?download_converted_file=0&sha256=" + sha256)
        return conn.getresponse().code == 200

    def delete_file(self, sha256):
        conn = http.client.HTTPConnection(self.db_conv_url)
        conn.request("GET", "?delete_file=1&sha256=" + sha256)
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

    def start_conversion_task_if_needed(self, filename, file_extension):
        if file_extension == DEFAULT_PDF_EXTENSION or is_archive_extension(file_extension):
            assert self.conversion_thread is not None
            self._add_file(filename, file_extension)

    def wait_doc_conversion_finished(self):
        try:
            self.wait_new_tasks = False
            self.conversion_thread.join()
            self._wait_conversion_tasks()
        except Exception as exp:
            self.logger.error("wait_doc_conversion_finished, exception caught: {}".format(exp))
