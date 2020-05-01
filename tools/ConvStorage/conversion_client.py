import time
import http.client
import logging
import urllib.request
import urllib.error
import threading
import hashlib
import os
import queue
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


class TInputTask:
    def __init__(self, file_path, file_extension, rebuild):
        self.file_path = file_path
        self.file_extension = file_extension
        self.rebuild = rebuild


class TDocConversionClient(object):
    def __init__(self, logger=None):
        global DECLARATOR_CONV_URL
        assert_declarator_conv_alive()
        self.wait_new_tasks = True
        self._input_tasks = queue.Queue()
        self.lock = threading.Lock()
        self._sent_tasks = list()
        self.conversion_thread = None
        self.db_conv_url = DECLARATOR_CONV_URL
        self.input_task_timeout = 5
        self.logger = logger if logger is not None else logging.getLogger("dlrobot_logger")

    def start_conversion_thread(self):
        self.conversion_thread = threading.Thread(target=self._process_files_to_convert_in_a_separate_thread, args=())
        self.conversion_thread.start()

    def _process_files_to_convert_in_a_separate_thread(self):
        while True:
            time.sleep(self.input_task_timeout)
            if self._input_tasks.empty() and not self.wait_new_tasks:
                break
            while not self._input_tasks.empty():
                task = self._input_tasks.get()
                if is_archive_extension(task.file_extension):
                    with TemporaryDirectory(prefix="conversion_folder", dir=".") as tmp_folder:
                        for archive_index, name_in_archive, export_filename in dearchive_one_archive(task.file_extension,
                                                                                                     task.file_path, 0,
                                                                                                     tmp_folder):
                            if export_filename.endswith(DEFAULT_PDF_EXTENSION):
                                self._send_file_to_conversion_db(export_filename, DEFAULT_PDF_EXTENSION, task.rebuild)
                else:
                    self._send_file_to_conversion_db(task.file_path, task.file_extension, task.rebuild)

    def _register_task(self, file_extension, file_contents, sha256, rebuild):
        conn = http.client.HTTPConnection(self.db_conv_url)
        if rebuild:
            path = '/convert_mandatory/file'
        else:
            path = '/convert_if_absent/file'
        path += file_extension
        conn.request("PUT", path, file_contents)
        response = conn.getresponse()
        if response.code != 201:
            self.logger.error("could not put a task to conversion queue")
        else:
            self.lock.acquire()
            try:
                self._sent_tasks.append(sha256)
            finally:
                self.lock.release()

    def _send_file_to_conversion_db(self, filename, file_extension, rebuild):
        try:
            with open(filename, "rb") as f:
                file_contents = f.read()
                hashcode = hashlib.sha256(file_contents).hexdigest()

            if hashcode in self._sent_tasks:
                return
            if not rebuild:
                if self.check_file_was_converted(hashcode):
                    return
            self.logger.debug("register conversion task for {}".format(filename))
            self._register_task(file_extension, file_contents, hashcode, rebuild)
        except Exception as exp:
            self.logger.error("cannot process {}: {}".format(filename, exp))

    def _wait_conversion_tasks(self, timeout_in_seconds=60*30):
        start_time = time.time()
        while len(self._sent_tasks) > 0:
            time.sleep(10)
            for sha256 in list(self._sent_tasks):
                if self.check_file_was_converted(sha256):
                    self.logger.debug("{} was converted".format(sha256))
                    self.lock.acquire()
                    try:
                        self._sent_tasks.remove(sha256)
                    finally:
                        self.lock.release()
            if time.time() > start_time + timeout_in_seconds:
                self.logger.error("timeout exit, {} conversion tasks were not completed".format(len(self._sent_tasks)))
                break

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

    def start_conversion_task_if_needed(self, filename, file_extension, rebuild=False):
        if file_extension == DEFAULT_PDF_EXTENSION or is_archive_extension(file_extension):
            assert self.conversion_thread is not None
            self._input_tasks.put(TInputTask(filename, file_extension, rebuild))
            return True
        return False

    def stop_conversion_thread(self):
        self.wait_new_tasks = False
        self.conversion_thread.join(1)

    def wait_doc_conversion_finished(self):
        try:
            if not self._input_tasks.empty():
                self.logger.debug("wait all conversion tasks to be sent to the server")
                while not self._input_tasks.empty():
                    time.sleep(1) # time to send tasks

            self.logger.debug("stop the input conversion client thread")
            self.wait_new_tasks = False
            self.conversion_thread.join(self.input_task_timeout + 1)

            self.logger.debug("wait the conversion server convert all files")
            self._wait_conversion_tasks()
        except Exception as exp:
            self.logger.error("wait_doc_conversion_finished: exception {}".format(exp))
