from ConvStorage.convert_storage import TConvertStorage
from common.primitives import build_dislosures_sha256_by_file_data, run_with_timeout
from common.logging_wrapper import  close_logger

import argparse
import json
import time
import http.server
import os
import re
import urllib
import shutil
import subprocess
import logging
import tempfile
import sys
import queue
from pathlib import Path
from logging.handlers import RotatingFileHandler
from http import HTTPStatus
import telegram_send
import threading


def convert_to_seconds(s):
    seconds_per_unit = {"s": 1, "m": 60, "h": 3600}
    if s is None or len(s) == 0:
        return 0
    if seconds_per_unit.get(s[-1]) is not None:
        return int(s[:-1]) * seconds_per_unit[s[-1]]
    else:
        return int(s)


def convert_pdf_to_docx_with_abiword(input_path, out_path):
    run_with_timeout(["abiword", '--to=docx', input_path])
    filename_wo_extenstion, _ = os.path.splitext(input_path)
    temp_outfile = filename_wo_extenstion + ".docx"
    if not os.path.exists(temp_outfile):
        return 1
    shutil.move(temp_outfile, out_path)


def taskkill_windows(process_name):
    subprocess.run(['taskkill', '/F', '/IM', process_name],  stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

def move_file_with_retry(logger, file_name, output_folder):
    output_file = os.path.join(output_folder, os.path.basename(file_name))
    for try_index in [1, 2, 3]:
        try:
            if os.path.exists(output_file):
                os.unlink(output_file)
            shutil.move(file_name, output_folder)
            return
        except Exception as exp:
            logger.error("cannot move {}, exception={}, wait 20 seconds...".format(file_name, exp))
            time.sleep(20)
    shutil.move(file_name, output_folder)


def setup_logging(logfilename):
    logger = logging.getLogger("db_conv_logger")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = RotatingFileHandler(logfilename, encoding="utf8", maxBytes=1024*1024*1024, backupCount=2)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def strip_drm(logger, filename, stripped_file):
    pdfcrack_path = 'pdfcrack'
    with open("crack.info", "w", encoding="utf8") as outf:
        subprocess.run([pdfcrack_path, filename], stderr=subprocess.DEVNULL, stdout=outf)
        logger.debug("{} {}".format(pdfcrack_path, filename))
    password = None
    with open("crack.info", "r") as log:
        prefix = "found user-password: "
        for l in log:
            if l.startswith(prefix):
                password = prefix[len(prefix):].strip("'")
    taskkill_windows('pdfcrack.exe')
    os.unlink("crack.info")
    qpdf = ['qpdf', '--decrypt']
    if password is not None:
        qpdf.append('--password={}'.format(password))
    qpdf.extend([filename, stripped_file])
    logger.debug(" ".join(qpdf))
    status = subprocess.run(qpdf, capture_output=True)
    if status.returncode != 0 or not os.path.exists(stripped_file) or Path(stripped_file).stat().st_size == 0:
        logger.error("qpdf failed on {}, error {} ".format(filename, status.stderr.decode('utf8')))
        logger.error("try to use the original file")
        shutil.copyfile(filename, stripped_file)


class TInputTask:
    def __init__(self, file_path, sha256, file_size, force, only_winword_conversion=False, only_ocr=False):
        self.file_path = file_path
        self.basename = os.path.basename(file_path)
        self.sha256 = sha256
        self.file_size = file_size
        self.creation_time = time.time()
        self.force = force
        self.only_winword_conversion = only_winword_conversion
        self.only_ocr = only_ocr


class TConvertProcessor(http.server.HTTPServer):
    pause_service_actions_file_path = ".pause"
    @staticmethod
    def parse_args(arglist):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable DECLARATOR_CONV_URL")
        parser.add_argument("--logfile", dest='logfile', default='db_conv.log')
        parser.add_argument("--db-json", dest='db_json', required=True)
        parser.add_argument("--clear-db", dest='clear_json', required=False, action="store_true")
        parser.add_argument("--disable-ocr", dest='enable_ocr', default=True, required=False, action="store_false")
        parser.add_argument("--use-abiword", dest='use_abiword', default=False, required=False, action="store_true",
                            help="use abiword to convert pdf to docx (test purposes)")
        parser.add_argument("--disable-winword", dest='enable_winword', default=True, required=False,
                            action="store_false")
        parser.add_argument("--input-folder", dest='input_folder', required=False, default="input_files")
        parser.add_argument("--input-folder-cracked", dest='input_folder_cracked', required=False,
                            default="input_files_cracked")
        parser.add_argument("--ocr-input-folder", dest='ocr_input_folder', required=False, default="pdf.ocr")
        parser.add_argument("--ocr-output-folder", dest='ocr_output_folder', required=False, default="pdf.ocr.out")
        parser.add_argument("--ocr-logs-folder", dest='ocr_logs_folder', required=False, default="ocr.logs")

        # max time between putting file to ocr queue and getting the result
        parser.add_argument("--ocr-timeout", dest='ocr_timeout', required=False,
                            help="delete file if ocr cannot process it in this timeout, default 3h",
                            default="3h")

        parser.add_argument("--winword-timeout", dest='winword_timeout', required=False,
                            help="stop winword (that was called by MicrosoftPdf2Docx) if it processes file longer than timeout",
                            default="60s")

        parser.add_argument("--microsoft-pdf-2-docx",
                            dest='microsoft_pdf_2_docx',
                            required=False,
                            default="C:/tmp/smart_parser/smart_parser/tools/MicrosoftPdf2Docx/bin/Debug/MicrosoftPdf2Docx.exe")
        parser.add_argument("--disable-killing-winword", dest='use_winword_exlusively', default=True, required=False,
                            action="store_false")
        parser.add_argument("--request-rate-serialize",
                            dest='request_rate_serialize', default=100, required=False, type=int,
                            help="save db on each Nth get request")

        # if the ocr queue is not empty and ocr produces no results in  1 hour, we have to restart ocr
        parser.add_argument("--ocr-restart-time", dest='ocr_restart_time', required=False,
                            help="restart ocr if it produces no results", default="3h")

        parser.add_argument("--central-heart-rate", dest='central_heart_rate', type=int, required=False, default='10')
        parser.add_argument("--bin-file-size", dest='user_bin_file_size', type=int, required=False)
        parser.add_argument("--disable-telegram", dest="enable_telegram",
                            default=True,  required=False, action="store_false")

        args = parser.parse_args(arglist)
        args.ocr_timeout = convert_to_seconds(args.ocr_timeout)
        args.ocr_restart_time = convert_to_seconds(args.ocr_restart_time)
        args.winword_timeout = convert_to_seconds(args.winword_timeout)
        if args.server_address is None:
            args.server_address = os.environ['DECLARATOR_CONV_URL']
        return args

    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(args.logfile)
        self.convert_storage = None

        self.server_actions_thread = None
        self.stop_input_thread = False
        self.input_task_queue = queue.Queue()
        self.ocr_tasks = dict()
        self.all_put_files_count = 0
        self.input_files_size = 0
        self.processed_files_size = 0
        self.failed_files_size = 0
        self.successful_get_requests = 0
        self.finished_ocr_tasks = 0
        self.hot_folder_path = None
        if sys.platform.startswith('win32'):
            self.hot_folder_path = self.get_hot_folder_path_from_running_tasks()
            if self.hot_folder_path is None:
                raise Exception("cannot find running HotFolder.exe")

        self.file_garbage_collection_timestamp = 0
        self.ocr_queue_is_empty_last_time_stamp = time.time()
        self.got_ocred_file_last_time_stamp = time.time()
        self.http_server_is_working = False
        self.convert_storage = TConvertStorage(self.logger, args.db_json, args.user_bin_file_size)
        self.continuous_winword_failures_count = 0
        if args.clear_json:
            self.convert_storage.clear_database()
        self.create_folders()
        host, port = self.args.server_address.split(":")
        super().__init__((host, int(port)), THttpServerRequestHandler)
        if shutil.which("qpdf") is None:
            msg = "cannot find qpdf, sudo apt install qpdf"
            self.logger.error(msg)
            raise Exception(msg)
        if shutil.which("pdfcrack") is None:
            msg = "cannot find pdfcrack\nsee https://sourceforge.net/projects/pdfcrack/files/"
            self.logger.error(msg)
            raise Exception(msg)
        self.send_to_telegram("conversion server started on {}".format(self.args.server_address))

    def get_hot_folder_path_from_running_tasks(self):
        p1 = subprocess.run(['wmic', 'process', 'get', 'ExecutablePath'], capture_output=True)
        for x in p1.stdout.decode('utf8', errors="ignore").split("\n"):
            if x.find('HotFolder.exe') != -1:
                return x.strip(" \r\n")

    def send_to_telegram(self, message):
        if self.args.enable_telegram:
            self.logger.debug("send to telegram: {}".format(message))
            telegram_send.send(messages=[message])

    def start_http_server(self):
        self.logger.debug("myServer.serve_forever(): {}".format(self.args.server_address))
        self.http_server_is_working = True
        self.server_actions_thread = threading.Thread(target=self.service_actions_in_a_thread)
        # Exit the server thread when the main thread terminates
        self.server_actions_thread.daemon = True
        self.server_actions_thread.start()
        try:
            self.serve_forever()
        except Exception as exp:
            self.logger.error("exit due exception {}".format(exp))
            self.stop_http_server()

    def stop_http_server(self, run_shutdown=True):
        if self.http_server_is_working:
            self.logger.debug("try to stop http server  ")
            self.http_server_is_working = False
            self.server_close()
            if run_shutdown:
                self.shutdown()
                self.server_actions_thread.join(1)
            try:
                if os.path.exists(self.args.input_folder_cracked):
                    shutil.rmtree(self.args.input_folder_cracked, ignore_errors=False)
            except Exception as exp:
                self.logger.error(exp)
            self.logger.debug("http server was stopped")
            self.convert_storage.close_storage()
            close_logger(self.logger)

    def save_new_file(self, sha256, file_bytes, file_extension, force, only_winword_conversion=False,
                      only_ocr=False):
        filename = os.path.join(self.args.input_folder, sha256 + file_extension)
        if os.path.exists(filename):  # already registered as an input task
            return False
        with open(filename, 'wb') as output_file:
            output_file.write(file_bytes)
        self.logger.debug("save new file {} ".format(filename))
        task = TInputTask(filename, sha256, len(file_bytes), force, only_winword_conversion=only_winword_conversion,
                          only_ocr=only_ocr)
        self.input_files_size += task.file_size
        self.input_task_queue.put(task)
        return True

    def register_file_process_finish(self, input_task: TInputTask, process_result):
        self.input_files_size -= input_task.file_size
        if process_result:
            self.processed_files_size += input_task.file_size
        else:
            self.failed_files_size += input_task.file_size

    def register_ocr_process_finish(self, input_task: TInputTask, process_result):
        if input_task is not None:
            self.register_file_process_finish(input_task, process_result)
            if input_task.sha256 in self.ocr_tasks:
                del self.ocr_tasks[input_task.sha256]
                self.finished_ocr_tasks += 1

    def kill_winword(self):
        if self.args.use_winword_exlusively:
            taskkill_windows('winword.exe')
        taskkill_windows('pdfreflow.exe')

    def convert_with_microsoft_word(self, filename):
        if not self.args.enable_winword:
            return
        self.logger.info("convert {} with microsoft word".format(filename))
        self.kill_winword()
        docx_file = filename + ".docx"
        try:
            status = subprocess.run([self.args.microsoft_pdf_2_docx, filename],
                       timeout=self.args.winword_timeout, capture_output=True)
            success = (status.returncode == 0 and os.path.exists(docx_file))
            if not success:
                winword_errors = status.stderr.decode("utf8").replace("\n", " ").strip()
                self.logger.debug(winword_errors)
        except Exception as exp:
            success = False
            self.logger.error("Exception {} in winword while processing {}".format(exp, filename))
            pass
        self.kill_winword()

        if success:
            self.continuous_winword_failures_count = 0
            return docx_file
        else:
            if not os.path.exists(docx_file) or os.path.getsize(docx_file) == 0:
                self.continuous_winword_failures_count += 1
                if self.continuous_winword_failures_count > 20:
                    self.send_to_telegram("pdf conversion server:continuous_winword_failures_count = {}".format(self.continuous_winword_failures_count))
            return None

    def process_one_input_file(self, input_task: TInputTask):
        input_file = input_task.file_path
        basename = os.path.basename(input_file)
        stripped_file = os.path.join(self.args.input_folder_cracked, basename)
        self.logger.debug("process input file {}, pwd={}".format(input_file, os.getcwd()))
        strip_drm(self.logger, input_file, stripped_file)

        docxfile = None if input_task.only_ocr else self.convert_with_microsoft_word(stripped_file)
        if docxfile is not None:
            self.convert_storage.delete_file_silently(stripped_file)
            self.convert_storage.save_converted_file(docxfile, input_task.sha256, "word", input_task.force)
            self.convert_storage.save_input_file(input_file)
            self.register_file_process_finish(input_task, True)
        else:
            if not self.args.enable_ocr or input_task.only_winword_conversion:
                self.logger.info("cannot process {}, delete it".format(input_file))
                self.convert_storage.delete_file_silently(input_file)
                self.convert_storage.delete_file_silently(stripped_file)
                self.register_file_process_finish(input_task, False)
            else:
                if self.args.use_abiword:
                    docx_path = stripped_file + ".docx"
                    self.logger.debug("abiword {} to {}".format(stripped_file, docx_path))
                    convert_pdf_to_docx_with_abiword(stripped_file, docx_path)
                    self.convert_storage.save_converted_file(docx_path, input_task.sha256, "abiword", input_task.force)
                    self.convert_storage.save_input_file(input_file)
                else:
                    self.logger.info("move {} to {}".format(stripped_file, self.args.ocr_input_folder))
                    move_file_with_retry(self.logger, stripped_file, self.args.ocr_input_folder)
                    self.convert_storage.save_input_file(input_file)
                    self.ocr_tasks[input_task.sha256] = input_task

    def create_cracked_folder(self):
        cracked_prefix = 'input_files_cracked'
        for x in os.listdir('.'):
            if x.startswith(cracked_prefix):
                self.logger.debug("rm {}".format(x))
                shutil.rmtree(x, ignore_errors=True)
        self.args.input_folder_cracked = tempfile.mkdtemp(prefix=cracked_prefix, dir=".")
        self.logger.debug("input_folder_cracked = {}".format(self.args.input_folder_cracked))
        assert os.path.isdir(self.args.input_folder_cracked)

    def create_folders(self):
        self.logger.debug("use {} as  microsoft word converter".format(self.args.microsoft_pdf_2_docx))

        if os.path.exists(self.args.input_folder):   #no way to process the input files without queue
            shutil.rmtree(self.args.input_folder, ignore_errors=True)
        if not os.path.exists(self.args.input_folder):
            os.mkdir(self.args.input_folder)
        if not os.path.exists(self.args.ocr_logs_folder):
            os.mkdir(self.args.ocr_logs_folder)
        self.logger.debug("input folder for new files: {} ".format(self.args.input_folder))

        if not os.path.exists(self.args.ocr_output_folder):
            os.mkdir(self.args.ocr_output_folder)
        if not os.path.exists(self.args.ocr_input_folder):
            os.mkdir(self.args.ocr_input_folder)
        if self.args.enable_winword:
            assert os.path.exists(self.args.microsoft_pdf_2_docx)
        self.create_cracked_folder()

    def process_ocr_logs(self):
        for log_file in os.listdir(self.args.ocr_output_folder):
            if not log_file.endswith(".txt"):
                continue
            broken_files = list()
            log_is_completed = False
            log_file_full_path = os.path.join(self.args.ocr_output_folder, log_file)
            try:
                with open(log_file_full_path, "r", encoding="utf-16-le", errors="ignore") as inp:
                    for line in inp:
                        if line.find('Error:') != -1:
                            m = re.search('[a-f0-9]{64}.pdf', line)
                            if m is not None:
                                file_path = os.path.join(self.args.ocr_input_folder, m.group(0))
                                broken_files.append(file_path)
                        if line.find('Pages processed') != -1:
                            log_is_completed = True
            except Exception as exp:
                self.logger.error("fail to read \"{}\", exception: {}".format(log_file, exp))
                continue

            if not log_is_completed:
                self.logger.debug("skip incomplete log_file \"{}\"".format(log_file))
                continue
            self.logger.debug("process log_file \"{}\" with {} broken files".format(log_file, len(broken_files)))
            try:
                shutil.move(log_file_full_path, os.path.join(self.args.ocr_logs_folder, log_file + "." + str(time.time())))
            except Exception as exp:
                self.logger.error("exception: {}".format(exp))

            for filename in broken_files:
                if os.path.exists(filename):
                    if not TConvertStorage.is_normal_input_file_name(filename):
                        self.convert_storage.delete_file_silently(filename)
                    else:
                        sha256 = TConvertStorage.get_sha256_from_filename(filename)
                        self.register_ocr_process_finish(self.ocr_tasks.get(sha256), False)
                        self.convert_storage.save_converted_file_broken_stub(sha256, True)
                        self.logger.debug("remove {}, since ocr cannot process it (\"{}\")".format(filename, log_file))
                        self.convert_storage.delete_file_silently(filename)

    def try_convert_with_winword(self):
        files_count = 0
        while not self.input_task_queue.empty():
            task = self.input_task_queue.get()
            try:
                self.process_one_input_file(task)
                files_count += 1
                if files_count >= 80:
                    break  # just give a chance to accomplish other tasks, then return to these tasks
            except Exception as exp:
                self.logger.error("Exception: {}".format(exp))
                if os.path.exists(task.file_path):
                    self.logger.error("delete {}".format(task.file_path))
                    os.unlink(task.file_path)

    def process_docx_from_ocr(self):
        new_files_in_db = False
        for docx_file in os.listdir(self.args.ocr_output_folder):
            if not docx_file.endswith(".docx"):
                continue
            docx_file = os.path.join(self.args.ocr_output_folder, docx_file)
            input_task = self.ocr_tasks.get(TConvertStorage.get_sha256_from_filename(docx_file))
            if input_task is None:
                self.logger.debug("remove a converted file from unknown sources ".format(docx_file))
                self.convert_storage.delete_file_silently(docx_file)
            else:
                for try_index in [1, 2, 3]:
                    self.logger.info("got file {} from ocr try to move it, trial No {}".format(docx_file, try_index))
                    try:
                        self.convert_storage.save_converted_file(docx_file, input_task.sha256, "ocr", input_task.force)
                        self.register_ocr_process_finish(input_task, True)
                        new_files_in_db = True
                        break
                    except Exception as exp:
                        # under windows it should raise an exception if ocr is still writing to this file
                        self.logger.error("Exception {}, sleep 60 seconds ...".format(str(exp)))
                        time.sleep(60)

                # delete tmp stripped pdf file, the input file is in storage
                self.convert_storage.delete_file_silently(os.path.join(self.args.ocr_input_folder, input_task.sha256 + ".pdf"))

                if os.path.exists(docx_file):
                    self.logger.debug("cannot access {} in 3 tries, remove it".format(docx_file))
                    self.register_ocr_process_finish(input_task, False)
                    self.convert_storage.delete_file_silently(docx_file)

        return new_files_in_db

    def get_stats(self):

        try:
            ocr_pending_all_file_size = sum(x.file_size for x in self.ocr_tasks.values())
            input_task_queue = self.input_task_queue.qsize()
            ocr_tasks_count = len(self.ocr_tasks)
            return {
                'all_put_files_count': self.all_put_files_count,
                'successful_get_requests_count': self.successful_get_requests,
                # normally input_task_queue == input_folder_files_count
                'input_task_queue': input_task_queue,
                'input_folder_files_count': len(os.listdir(self.args.input_folder)),

                # normally ocr_pending_files_count == ocr_tasks_count
                'ocr_pending_files_count': len(os.listdir(self.args.ocr_input_folder)),
                'ocr_tasks_count': ocr_tasks_count,
                'ocr_pending_all_file_size': ocr_pending_all_file_size,

                'is_converting': input_task_queue > 0 or ocr_tasks_count > 0,
                'processed_files_size': self.processed_files_size,
                'failed_files_size': self.failed_files_size,
                'finished_ocr_tasks': self.finished_ocr_tasks,
                'snow_ball_os_error_count': self.convert_storage.snow_ball_os_error_count,
                "pause_service_actions": self.pause_service_actions(),
            }
        except Exception as exp:
            return {"exception": str(exp)}

    def process_stalled_files(self):
        current_time = time.time()
        for pdf_file in os.listdir(self.args.ocr_input_folder):
            fpath = os.path.join(self.args.ocr_input_folder, pdf_file)
            timestamp = Path(fpath).stat().st_mtime
            if current_time - timestamp > self.args.ocr_timeout:
                self.logger.error("delete orphan file {} after stalling {} seconds".format(
                    fpath, self.args.ocr_timeout))
                self.convert_storage.delete_file_silently(fpath)
                sha256 = TConvertStorage.get_sha256_from_filename(pdf_file)
                self.register_ocr_process_finish(self.ocr_tasks.get(sha256), False)

    def restart_ocr(self):
        self.logger.debug("restart ocr")
        self.logger.debug("taskkill HotFolder.exe");
        taskkill_windows('HotFolder.exe')

        self.logger.debug("taskkill fineexec.exe");
        taskkill_windows('FineExec.exe')

        self.logger.debug("start HotFolder.exe")
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | \
                                subprocess.CREATE_BREAKAWAY_FROM_JOB | subprocess.SW_HIDE
        subprocess.Popen([self.hot_folder_path], creationflags=creationflags, stdin=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, cwd="c:/")

    def process_all_tasks(self):
        if len(self.ocr_tasks) == 0:
            self.ocr_queue_is_empty_last_time_stamp = time.time()
        self.try_convert_with_winword()
        new_files_from_ocr = self.process_docx_from_ocr()
        if new_files_from_ocr:
            self.got_ocred_file_last_time_stamp = time.time()
        # file garbage tasks
        current_time = time.time()
        if current_time - self.file_garbage_collection_timestamp >= 60:  # just not too often
            self.file_garbage_collection_timestamp = current_time
            self.process_ocr_logs()
            self.process_stalled_files()

        current_time = time.time()
        if  current_time - self.got_ocred_file_last_time_stamp > self.args.ocr_restart_time and \
                current_time - self.ocr_queue_is_empty_last_time_stamp > self.args.ocr_restart_time :
            self.logger.debug("last ocr file was received long ago and all this time the ocr queue was not empty")
            self.restart_ocr()
            self.got_ocred_file_last_time_stamp = time.time()  #otherwize restart will be too often

    def pause_service_actions(self):
        return os.path.exists(self.pause_service_actions_file_path)

    def service_actions_in_a_thread(self):
        last_heart_beat = time.time()
        while self.http_server_is_working:
            if time.time() - last_heart_beat >= self.args.central_heart_rate:
                if not self.pause_service_actions():
                    try:
                        self.process_all_tasks()
                    except Exception as exp:
                        if self.logger is not None:
                            self.logger.error(exp)
                        self.stop_http_server(run_shutdown=False)
                        sys.exit(1)
                last_heart_beat = time.time()
            else:
                time.sleep(1)


ALLOWED_FILE_EXTENSTIONS={'.pdf'}


class THttpServerRequestHandler(http.server.BaseHTTPRequestHandler):

    def parse_cgi(self, query_components):
        query = urllib.parse.urlparse(self.path).query
        if query == "":
            return True
        for qc in query.split("&"):
            items = qc.split("=")
            if len(items) != 2:
                return False
            query_components[items[0]] = items[1]
        return True

    def log_message(self, msg_format, *args):
        self.server.logger.debug(msg_format % args)

    def log_request(self, code='-', size='-'):
        aux_params = str(self.client_address[0])
        if hasattr(self, "last_error_message") and self.last_error_message != "":
            aux_params += " error: " + self.last_error_message
        self.log_message("%s %s %s from %s",  self.requestline, str(code), str(size), aux_params)

    def process_special_commands(self):
        if self.path == "/ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"yes")
            return True
        if self.path == "/stat":
            self.send_response(200)
            self.end_headers()
            stats = json.dumps(self.server.get_stats())
            self.wfile.write(stats.encode("utf8"))
            return True
        return False

    def send_error_404(self, message):
        self.last_error_message = message
        self.send_error(HTTPStatus.NOT_FOUND, message)
        #self.server.logger.error(message)

    def _do_GET(self):
        if self.process_special_commands():
            return

        query_components = dict()
        if not self.parse_cgi(query_components):
            self.send_error_404('bad request')
            return

        sha256 = query_components.get('sha256', None)
        if not sha256:
            self.send_error_404('No SHA256 provided')
            return

        file_contents, _ = self.server.convert_storage.get_converted_file(sha256)
        if file_contents is None:
            self.send_error_404('File not found')
            return

        self.send_response(200)
        self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        self.end_headers()
        self.server.convert_storage.register_access_request(sha256)
        self.server.successful_get_requests += 1;
        if query_components.get("download_converted_file", True):
            self.wfile.write(file_contents)

    def do_GET(self):
        try:
            self.last_error_message = ""
            return self._do_GET()
        except (OSError, UnicodeError) as exp:
            self.send_error_404(str(exp))

    def _do_PUT(self):
        if self.path is None:
            self.send_error_404("no file specified")
            return
        action = os.path.dirname(self.path)
        query_components = dict()
        if not self.parse_cgi(query_components):
            self.send_error_404('bad request')
            return

        _, file_extension = os.path.splitext(os.path.basename(self.path))
        if file_extension.find('?') != -1:
            file_extension = file_extension[:file_extension.find('?')]
        action = action.strip('//')
        if action == "convert_if_absent":
            rebuild = False
        elif action == "convert_mandatory":
            rebuild = True
        else:
            self.send_error_404("bad action (file path), can be 'convert_mandatory' or 'convert_if_absent', got \"{}\"".format(action))
            return
        if file_extension not in ALLOWED_FILE_EXTENSTIONS:
            self.send_error_404("bad file extension: {}, can be {}".format(file_extension, ALLOWED_FILE_EXTENSTIONS))
            return

        file_length = int(self.headers['Content-Length'])
        max_file_size = 2**25
        if file_length > max_file_size:
            self.send_error_404("file is too large (size must less than {} bytes ".format(max_file_size))
            return
        self.server.logger.debug("receive file {} length {}".format(self.path, file_length))
        try:
            file_bytes = self.rfile.read(file_length)
        except ConnectionError as exp:
            self.send_error_404("ConnectionError : {}".format(exp))
            return

        sha256 = build_dislosures_sha256_by_file_data(file_bytes, file_extension)
        if not rebuild and self.server.convert_storage.has_converted_file(sha256):
            self.send_response(201, 'Already exists')
            self.end_headers()
            return
        if not self.server.save_new_file(sha256, file_bytes,  file_extension, rebuild,
                                     only_winword_conversion=query_components.get("only_winword_conversion", False),
                                    only_ocr=query_components.get("only_ocr", False)):
            self.send_response(201, 'Already registered as a conversion task, wait ')
            self.end_headers()
            return

        self.server.all_put_files_count += 1

        self.send_response(201, 'Cre    ated')
        self.end_headers()

    def do_PUT(self):
        try:
            self.last_error_message = ""
            return self._do_PUT()
        except (OSError, UnicodeError) as exp:
            self.send_error_404(str(exp))


def conversion_server_main(args):
    server = TConvertProcessor(args)
    exit_code = 0
    try:
        server.start_http_server()
    except Exception as exp:
        server.logger.error("general exception: {}".format(exp))
        exit_code = 1
    server.stop_http_server()
    server.logger.debug("reach the end of the main")
    return exit_code


if __name__ == '__main__':
    args = TConvertProcessor.parse_args(sys.argv[1:])
    try:
        exit_code = conversion_server_main(args)
    except KeyboardInterrupt as exp:
        sys.stderr.write("ctrl+c received, exception\n")
        exit_code = 1
    sys.exit(exit_code)