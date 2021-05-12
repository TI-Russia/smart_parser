from common.archives import TDearchiver
from common.primitives import build_dislosures_sha256
from common.content_types import DEFAULT_PDF_EXTENSION
from ConvStorage.convert_storage import TConvertStorage

import time
import http.client
import logging
import urllib.request
import urllib.error
import threading
import os
import queue
import json
from tempfile import TemporaryDirectory
from pathlib import Path
import argparse


class TInputTask:
    def __init__(self, file_path, file_extension, rebuild):
        self.file_path = file_path
        self.file_extension = file_extension
        self.rebuild = rebuild


class TDocConversionClient(object):
    DECLARATOR_CONV_URL = os.environ.get('DECLARATOR_CONV_URL')
    MAX_FILE_PENDING_SUM_SIZE = 100 * 2 ** 20  # if pending file size sum is greater than MAX_FILE_PENDING_SUM_SIZE,
                                               # then we should stop sending new files

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument('input', nargs='*')
        parser.add_argument("--rebuild", dest='rebuild_pdf', action="store_true", default=False)
        parser.add_argument("--conversion-timeout", dest='conversion_timeout', type=int, default=60 * 30)
        parser.add_argument("--conversion-server", "--server-address", dest='conversion_server', required=False)
        parser.add_argument("--skip-receiving", dest='receive_files', default=True, action="store_false",
                            required=False)
        parser.add_argument("--output-folder", dest='output_folder', default=None, required=False)
        parser.add_argument("--only-winword", dest='only_winword', default=False, required=False, action="store_true")
        parser.add_argument("--only-ocr", dest='only_ocr', default=False, required=False, action="store_true")
        TDocConversionClient.DECLARATOR_CONV_URL = os.environ.get('DECLARATOR_CONV_URL') #reread for tests
        return parser.parse_args(arg_list)

    def __init__(self, args, logger=None):
        self.args = args
        if args.conversion_server is not None:
            TDocConversionClient.DECLARATOR_CONV_URL = args.conversion_server
        self.logger = logger if logger is not None else logging.getLogger("dlrobot_logger")
        if TDocConversionClient.DECLARATOR_CONV_URL is None:
            print("specify environment variable DECLARATOR_CONV_URL to obtain docx by pdf-files")
            assert TDocConversionClient.DECLARATOR_CONV_URL is not None
        assert_declarator_conv_alive(self.logger)
        self.wait_new_tasks = True
        self._input_tasks = queue.Queue()
        self._sent_tasks = list()
        self.conversion_thread = None
        self.db_conv_url = TDocConversionClient.DECLARATOR_CONV_URL
        self.input_task_timeout = 5
        self.all_pdf_size_sent_to_conversion = 0
        self.default_http_timeout = 60*10
        self.inner_stats_timestamp = None
        self.last_pdf_conversion_queue_length = None

    def update_inner_stats(self):
        self.inner_stats_timestamp = time.time()
        stats = self.get_stats()
        if stats is None:
            self.last_pdf_conversion_queue_length = 200 * 2 ** 20  # just an unknown number, terror magnifies objects
        else:
            self.last_pdf_conversion_queue_length = stats['ocr_pending_all_file_size']

    def server_is_too_busy(self):
        if self.inner_stats_timestamp is None or time.time() > self.inner_stats_timestamp + 4*60:
            self.update_inner_stats()  # update inner stats each 5 minutes
        return self.last_pdf_conversion_queue_length >= TDocConversionClient.MAX_FILE_PENDING_SUM_SIZE

    def start_conversion_thread(self):
        self.conversion_thread = threading.Thread(target=self._process_files_to_convert_in_a_separate_thread, args=())
        self.conversion_thread.start()

    def _process_files_to_convert_in_a_separate_thread(self):
        while self.wait_new_tasks:
            try:
                task = self._input_tasks.get(timeout=self.input_task_timeout)
            except queue.Empty as exp:
                continue
            if TDearchiver.is_archive_extension(task.file_extension):
                with TemporaryDirectory(prefix="conversion_folder", dir=".") as tmp_folder:
                    dearchiver = TDearchiver(self.logger, tmp_folder)
                    for archive_index, name_in_archive, export_filename in dearchiver.dearchive_one_archive(
                                        task.file_extension, task.file_path, 0,):
                        if export_filename.endswith(DEFAULT_PDF_EXTENSION):
                            self._send_file_to_conversion_db(export_filename, DEFAULT_PDF_EXTENSION, task.rebuild)
            else:
                self._send_file_to_conversion_db(task.file_path, task.file_extension, task.rebuild)
            self._input_tasks.task_done()

    def _register_task(self, file_extension, file_contents, sha256, rebuild):
        conn = http.client.HTTPConnection(self.db_conv_url, timeout=self.default_http_timeout)
        if rebuild:
            path = '/convert_mandatory/file'
        else:
            path = '/convert_if_absent/file'
        path += file_extension
        if self.args.only_winword:
            path += "?only_winword_conversion=1"
        if self.args.only_ocr:
            path += "?only_ocr=1"
        try:
            conn.request("PUT", path, file_contents)
            response = conn.getresponse()
            if response.code != 201:
                self.logger.error("could not put a task to conversion queue: http code={}".format(response.code))
                return False
            else:
                self._sent_tasks.append(sha256)
            return True
        except http.client.HTTPException as exp:
            self.logger.error("got exception {} in _register_task ".format(str(exp)))
            return False
        except TimeoutError as exp:
            self.logger.error("got exception {} in check_file_was_converted, timeout={} ".format(
                str(exp), self.default_http_timeout))
            return False

    def _send_file_to_conversion_db(self, filename, file_extension, rebuild):
        with open(filename, "rb") as f:
            file_contents = f.read()
            starter = file_contents[:5].decode('latin', errors="ignore")
            if starter != '%PDF-':
                self.logger.debug("{} has bad pdf starter, do  not send it".format(filename))
                return
        hashcode = build_dislosures_sha256(filename)
        if hashcode in self._sent_tasks:
            return

        if not rebuild:
            if self.check_file_was_converted(hashcode):
                return
        self.logger.debug("register conversion task for {}".format(filename))
        if self._register_task(file_extension, file_contents, hashcode, rebuild):
            self.all_pdf_size_sent_to_conversion += Path(filename).stat().st_size

    def _wait_conversion_tasks(self, timeout_in_seconds):
        self.logger.debug("wait the conversion server convert all files for {} seconds".format(timeout_in_seconds))
        end_time = time.time() + timeout_in_seconds
        self.logger.info("number of conversion tasks to be waited: {}".format(len(self._sent_tasks)))
        while len(self._sent_tasks) > 0 and time.time() < end_time:
            for sha256 in list(self._sent_tasks):
                if self.check_file_was_converted(sha256):
                    self.logger.debug("{} was converted".format(sha256))
                    self._sent_tasks.pop(0)
                else:
                    break
            if len(self._sent_tasks) > 0:
                time.sleep(10)

        if len(self._sent_tasks) > 0:
            self.logger.info("timeout exit, {} conversion tasks were not completed".format(len(self._sent_tasks)))

    def check_file_was_converted(self, sha256):
        conn = http.client.HTTPConnection(self.db_conv_url, timeout=self.default_http_timeout)
        try:
            conn.request("GET", "?download_converted_file=0&sha256=" + sha256)
            return conn.getresponse().code == 200
        except http.client.HTTPException as exp:
            self.logger.error("got exception {} in check_file_was_converted ".format(str(exp)))
            return False
        except TimeoutError as exp:
            self.logger.error("got exception {} in check_file_was_converted, timeout={} ".format(
                str(exp), self.default_http_timeout))
            return False

    def get_stats(self):
        data = None
        try:
            conn = http.client.HTTPConnection(self.db_conv_url, timeout=self.default_http_timeout)
            conn.request("GET", "/stat")
            response = conn.getresponse()
            data = response.read().decode('utf8')
            return json.loads(data)
        except Exception as exp:
            message = "conversion_client, get_stats failed: {}".format(exp)
            if data is not None:
                message += "; conversion server answer was {}".format(data)
            self.logger.error(message)
            return None
        except TimeoutError as exp:
            self.logger.error("got exception {} in check_file_was_converted, timeout={} ".format(
                str(exp), self.default_http_timeout))
            return None

    def retrieve_document(self, sha256, output_file_name, verbose=False):
        # retrieve_document returns True, if file was processed by the server.
        # If the server  found an error in pdf it returned TConvertStorage.broken_stub.
        # If the server return TConvertStorage.broken_stub we do not create a file, but return True.
        conn = http.client.HTTPConnection(self.db_conv_url, timeout=self.default_http_timeout)
        try:
            conn.request("GET", "?sha256=" + sha256)
            response = conn.getresponse()
            if response.code == 200:
                file_content = response.read()
                if file_content != TConvertStorage.broken_stub:
                    with open(output_file_name, "wb") as out:
                        out.write(file_content)
                return True
            else:
                if verbose:
                    self.logger.debug("cannot get docx by sha256={} http code={}".format(
                        sha256,response.code
                    ))
                return False
        except http.client.HTTPException as exp:
            self.logger.error("got exception {} in retrieve_document ".format(str(exp)))
            return False
        except TimeoutError as exp:
            self.logger.error("got exception {} in check_file_was_converted, timeout={} ".format(
                str(exp), self.default_http_timeout))
            return False

    @staticmethod
    def is_acceptable_file_extension(file_extension):
        return file_extension == DEFAULT_PDF_EXTENSION or TDearchiver.is_archive_extension(file_extension)

    def start_conversion_task_if_needed(self, filename, file_extension, rebuild=False):
        if not self.is_acceptable_file_extension(file_extension):
            return False
        max_file_size = 2 ** 25
        if Path(filename).stat().st_size  > max_file_size:
            self.logger.debug("file {} is too large for conversion (size must less than {} bytes) ".format(
                filename, max_file_size))
            return False
        assert self.conversion_thread is not None
        self._input_tasks.put(TInputTask(filename, file_extension, rebuild))
        return True

    def stop_conversion_thread(self, timeout=None):
        if timeout is None:
            timeout = self.input_task_timeout + 1
        if self.conversion_thread is not None:
            self.logger.debug("stop the input conversion client thread")
            self.wait_new_tasks = False
            self.conversion_thread.join(timeout)
            self.conversion_thread = None

    def wait_all_tasks_to_be_sent(self):
        self.logger.debug("wait all conversion tasks to be sent to the server")
        self._input_tasks.join()

    def wait_doc_conversion_finished(self, timeout_in_seconds):
        try:
            self.wait_all_tasks_to_be_sent()
            self.stop_conversion_thread()
            self._wait_conversion_tasks(timeout_in_seconds)
        except Exception as exp:
            self.logger.error("wait_doc_conversion_finished: exception {}".format(exp))

    def send_files(self):
        sent_files = set()
        for filepath in self.args.input:
            _, extension = os.path.splitext(filepath)
            if self.start_conversion_task_if_needed(filepath, extension.lower(), self.args.rebuild_pdf):
                self.logger.debug("send {}".format(filepath))
                sent_files.add(filepath)
        return sent_files

    def receive_files(self, sent_files):
        errors_count = 0
        for filepath in sent_files:
            self.logger.debug("download docx for {}".format(filepath))
            sha256hash = build_dislosures_sha256(filepath)
            outfile = filepath + ".docx"
            if self.args.output_folder is not None:
                outfile = os.path.join(self.args.output_folder, os.path.basename(outfile))
            if self.retrieve_document(sha256hash, outfile):
                if os.path.exists(outfile):
                    self.logger.debug("save {}".format(outfile))
            else:
                self.logger.error("cannot download docx for file {}".format(filepath))
                errors_count += 1
        return errors_count == 0

    def process_files(self):
        sent_files = set()
        start_time = time.time()
        try:
            sent_files = self.send_files()
            if self.args.receive_files and len(sent_files) > 0:
                self.wait_doc_conversion_finished(self.args.conversion_timeout)
            else:
                self.logger.debug("stop conversion finished")
                self.stop_conversion_thread(timeout=1)
        except Exception as exp:
            self.logger.error("exception: {}, stop_conversion_thread".format(exp))
            self.stop_conversion_thread(timeout=1)
        if self.args.receive_files and time.time() - start_time < self.args.conversion_timeout:
            if not self.receive_files(sent_files):
                return 1
        return 0


def assert_declarator_conv_alive(logger=None):
    if TDocConversionClient.DECLARATOR_CONV_URL is None:
        raise Exception("environment variable DECLARATOR_CONV_URL is not set")

    try:
        url = "http://" + TDocConversionClient.DECLARATOR_CONV_URL+"/ping"
        if logger is not None:
            logger.debug ("try to ping pdf conversion server {}".format(url))
        with urllib.request.urlopen(url, timeout=300) as response:
            if response.read() == "yes":
                return True
    except Exception as exp:
        print("cannot connect to {} (declarator conversion server)".format(TDocConversionClient.DECLARATOR_CONV_URL))
        raise
