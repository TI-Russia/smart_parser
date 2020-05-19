import argparse
import json
import time
import http.server
import os
import re
import urllib
import hashlib
import shutil
import subprocess
import logging
import threading
import tempfile
import sys
import queue
from DeclDocRecognizer.document_types import TCharCategory
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-address", dest='server_address', default=None, help="by default read it from environment variable DECLARATOR_CONV_URL")
    parser.add_argument("--logfile", dest='logfile', default='db_conv.log')
    parser.add_argument("--db-json", dest='db_json', required=True)
    parser.add_argument("--clear-json", dest='clear_json', required=False, action="store_true")
    parser.add_argument("--disable-ocr", dest='enable_ocr', default=True, required=False, action="store_false")
    parser.add_argument("--input-folder", dest='input_folder', required=False, default="input_files")
    parser.add_argument("--input-folder-cracked", dest='input_folder_cracked', required=False, default="input_files_cracked")
    parser.add_argument("--ocr-input-folder", dest='ocr_input_folder', required=False, default="pdf.ocr")
    parser.add_argument("--ocr-output-folder", dest='ocr_output_folder', required=False, default="pdf.ocr.out")
    parser.add_argument("--ocr-logs-folder", dest='ocr_logs_folder', required=False, default="ocr.logs")
    parser.add_argument("--microsoft-pdf-2-docx",
                        dest='microsoft_pdf_2_docx',
                        required=False,
                        default="C:/tmp/smart_parser/smart_parser/tools/MicrosoftPdf2Docx/bin/Debug/MicrosoftPdf2Docx.exe")
    return parser.parse_args()


def setup_logging(logger, logfilename):
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.INFO)
    #logger.addHandler(ch)


def get_directory_size(logger, dir):
    dir_size = 0
    for x in os.listdir(dir):
        try:
            if os.path.exists(x):
                dir_size += Path(x).stat()
        except Exception as exp:
            logger.error(exp)

    return dir_size


def find_new_files_and_add_them_to_json(conv_db_json, converted_files_folder, output_file):
    if conv_db_json is None:
        conv_db_json = {
            "files": {}
        }
    conv_db_json["directory"] = os.path.realpath(converted_files_folder)

    registered_files = set()
    for x in conv_db_json['files'].values():
        registered_files.add(x['input'])

    for docxfile in os.listdir(conv_db_json['directory']):
        if not docxfile.endswith(".docx"):
            continue
        pdf_file_basename = docxfile[:-len(".docx")]
        if pdf_file_basename in registered_files:
            continue
        pdf_file = os.path.join(conv_db_json["directory"],  pdf_file_basename)
        if not os.path.exists(pdf_file):
            continue
        with open(pdf_file, "rb") as f:
            sha256hash = hashlib.sha256(f.read()).hexdigest();

        if sha256hash in conv_db_json['files']:
            if conv_db_json['files'][sha256hash]['input_file_size'] != os.path.getsize(pdf_file):
                print("Error! Collision found on {}".format(pdf_file))  # black swan or some error
                exit(1)
            continue

        conv_db_json['files'][sha256hash] = {
                'input_file_size': os.path.getsize(pdf_file),
                'converted': docxfile,
                'input': pdf_file_basename
        }
    with open(output_file, "w") as outf:
        json.dump(conv_db_json, outf, indent=4)


def strip_drm(logger, filename, stripped_file):
    with open("crack.info", "w", encoding="utf8") as outf:
        subprocess.run(['pdfcrack', filename], stderr=subprocess.DEVNULL, stdout=outf)
        logger.debug("pdfcrack {}".format(filename))
    password = None
    with open("crack.info", "r") as log:
        prefix = "found user-password: "
        for l in log:
            if l.startswith(prefix):
                password = prefix[len(prefix):].strip("'")
    os.unlink("crack.info")
    if password is not None:
        logger.debug("run qpdf on {} with password {}".format(filename, password))
        subprocess.run(['qpdf', '--password={}'.format(password), '--decrypt', filename, stripped_file],
                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        return True
    return False


def taskkill_windows(process_name):
    subprocess.run(['taskkill', '/F', '/IM', process_name],  stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)


def convert_with_microsoft_word(logger, microsoft_pdf_2_docx, filename):
    taskkill_windows('winword.exe')
    taskkill_windows('pdfreflow.exe')

    with tempfile.NamedTemporaryFile(prefix="microsoft_pdf_2_docx.log", dir=".") as log_file:
        subprocess.run([microsoft_pdf_2_docx, filename], timeout=60*10, stderr=log_file, stdout=log_file)
        try:
            log_file.seek(0)
            log_data = log_file.read().decode("utf8").replace("\n", " ").strip()
            logger.debug(log_data)
        except Exception as exp:
            pass

    taskkill_windows('winword.exe')
    taskkill_windows('pdfreflow.exe')


def delete_file_if_exists(logger, full_path):
    try:
        if os.path.exists(full_path):
            logger.debug("delete {}".format(full_path))
            os.unlink(full_path)
    except Exception as exp:
        logger.error("Exception {}, cannot delete {}, do not know how to deal with it...".format(exp, full_path))


class TInputTask:
    def __init__(self, file_path, sha256):
        self.file_path = file_path
        self.sha256 = sha256


class TConvDatabase:
    def __init__(self, args):
        self.args = args
        self.conv_db_json_file_name = args.db_json

        with open(args.db_json, "r", encoding="utf8") as inp:
            self.conv_db_json = json.load(inp)
        self.converted_files_folder = self.conv_db_json['directory']
        self.modify_json_lock = threading.Lock()
        assert "files" in self.conv_db_json
        if args.clear_json:
            self.conv_db_json['files'] = dict()
            self.save_json()
        self.logger = logging.getLogger("db_conv_logger")
        self.input_thread = None
        self.stop_input_thread = False
        self.input_task_queue = queue.Queue()
        self.all_put_files_count = 0

    def get_converted_file_name(self, sha256):
        value = self.conv_db_json['files'].get(sha256)
        if value is not None:
            return os.path.join(self.converted_files_folder, value["converted"])
        else:
            return None

    def get_input_file_name(self, sha256):
        value = self.conv_db_json['files'].get(sha256)
        if value is not None:
            return os.path.join(self.converted_files_folder, value["input"])
        else:
            return None

    def save_new_file(self, sha256, file_bytes, file_extension):
        filename = os.path.join(self.args.input_folder, sha256 + file_extension)
        if os.path.exists(filename):  # already registered as an input task
            return False
        with open(filename, 'wb') as output_file:
            output_file.write(file_bytes)
        self.logger.debug("save new file {} ".format(filename))
        task = TInputTask(filename, sha256)
        self.input_task_queue.put(task)
        return True

    def move_one_ocred_file(self, some_file):
        assert some_file.endswith(".docx")
        pdf_file = some_file[:-len(".docx")]
        input_file = os.path.join(self.converted_files_folder, pdf_file)
        converted_file = os.path.join(self.args.ocr_output_folder, some_file)
        delete_file_if_exists(self.logger, os.path.join(self.args.ocr_input_folder, pdf_file))
        if not os.path.exists(input_file):
            self.logger.debug(
                "cannot find the input file {}, remove converted file {} ".format(input_file, converted_file))
            delete_file_if_exists(self.logger, converted_file)
        else:
            output_file = os.path.join(self.converted_files_folder, some_file)
            logger.debug("move {} to {}".format(converted_file, output_file))
            shutil.move(converted_file, output_file)

    def process_one_input_file(self, input_file):
        basename = os.path.basename(input_file)
        stripped_file = os.path.join(self.args.input_folder_cracked, basename)
        self.logger.debug("process input file {}, pwd={}".format(input_file, os.getcwd()))
        if not strip_drm(self.logger, input_file, stripped_file):
            shutil.copyfile(input_file, stripped_file)
        self.logger.info("convert {} with microsoft word".format(input_file))
        convert_with_microsoft_word(self.logger, self.args.microsoft_pdf_2_docx, stripped_file)
        docxfile = stripped_file + ".docx"
        if os.path.exists(docxfile):
            self.logger.info("move {} and {} to {}".format(input_file, docxfile, self.converted_files_folder))
            shutil.move(docxfile, os.path.join(self.converted_files_folder, basename + ".docx"))
            shutil.move(input_file, os.path.join(self.converted_files_folder, basename))
            os.unlink(stripped_file)
        else:
            if not self.args.enable_ocr:
                self.logger.info("cannot process {}, delete it".format(input_file))
                os.unlink(input_file)
                os.unlink(stripped_file)
            else:
                self.logger.info("move {} to {}".format(stripped_file, self.args.ocr_input_folder))
                shutil.move(stripped_file, os.path.join(self.args.ocr_input_folder, basename))
                shutil.move(input_file, os.path.join(self.converted_files_folder, basename))

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
        if not os.path.exists(self.converted_files_folder):
            os.mkdir(self.converted_files_folder)

        assert os.path.exists(self.args.microsoft_pdf_2_docx)
        self.args.input_folder_cracked = tempfile.mkdtemp(prefix="input_files_cracked", dir=".")

    # can only add new files
    def rebuild_json_wrapper(self):
        self.logger.info("rebuild json started, files number={}".format(len(self.conv_db_json["files"])))
        self.modify_json_lock.acquire()
        try:
            find_new_files_and_add_them_to_json(self.conv_db_json,
                                              self.converted_files_folder,
                                              self.conv_db_json_file_name)
        finally:
            self.modify_json_lock.release()
        self.logger.info("rebuild json finished, files number={}".format(len(self.conv_db_json["files"])))

    def save_json(self):
        with open(self.conv_db_json_file_name, "w") as outf:
            json.dump(self.conv_db_json, outf, indent=4)

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
                        m = re.match('.*Error:.*: ([^ ]+.pdf)$', line)
                        if m is not None:
                            broken_files.append(m.group(1))
                        if line.find('Pages processed') != -1:
                            log_is_completed = True
            except Exception as exp:
                self.logger.error("fail to read \"{}\", exception: {}".format(log_file, exp))
                continue

            if not log_is_completed:
                self.logger.debug("skip incompleted log_file \"{}\"".format(log_file))
                continue
            self.logger.debug("process log_file \"{}\" with {} broken files".format(log_file, len(broken_files)))
            try:
                shutil.move(log_file_full_path, os.path.join(self.args.ocr_logs_folder, log_file + "." + str(time.time())))
            except Exception as exp:
                self.logger.error("exception: {}".format(exp))
            for filename in broken_files:
                if os.path.exists(filename):
                    self.logger.debug("remove {}, since ocr cannot process it (\"{}\")".format(filename, log_file))
                    delete_file_if_exists(self.logger, filename)

    def process_docx_from_winword(self):
        new_files_in_db = False
        while not self.input_task_queue.empty():
            task = self.input_task_queue.get()
            try:
                self.process_one_input_file(task.file_path)
                new_files_in_db = True
            except Exception as exp:
                self.logger.error("Exception: {}".format(exp))
                if os.path.exists(task.file_path):
                    self.logger.error("delete {}".format(task.file_path))
                    os.unlink(task.file_path)
        return new_files_in_db

    def process_docx_from_ocr(self):
        new_files_in_db = False
        for some_file in os.listdir(self.args.ocr_output_folder):
            if not some_file.endswith(".docx"):
                continue
            for try_index in [1, 2, 3]:
                self.logger.info("got file {} from finereader try to move it, trial No {}".format(some_file, try_index))
                try:
                    self.move_one_ocred_file(some_file)
                    new_files_in_db = True
                    break
                except Exception as exp:
                    self.logger.error("Exception {}, sleep 60 seconds ...".format(str(exp)))
                    time.sleep(60)
            delete_file_if_exists(logger, os.path.join(args.ocr_output_folder, some_file))
        return new_files_in_db

    def get_stats(self):
        try:
            return {
                'all_put_files_count': self.all_put_files_count,
                'input_task_queue': self.input_task_queue.qsize(),
                'ocr_pending_files_count': len(os.listdir(self.args.ocr_input_folder)),
                'ocr_pending_all_file_size': get_directory_size(self.logger, self.args.ocr_input_folder),
                'winword_input_queue_size': len(os.listdir(self.args.input_folder)),
            }
        except Exception as exp:
            return {"exception": str(exp)}

    def process_input_tasks(self):
        save_files_count = -1
        while not self.stop_input_thread:
            time.sleep(10)
            new_files_from_winword = self.process_docx_from_winword()
            new_files_from_ocr = self.process_docx_from_ocr()
            if new_files_from_winword or new_files_from_ocr:
                self.rebuild_json_wrapper()

            self.process_ocr_logs()
            files_count = len(os.listdir(self.args.ocr_input_folder))
            if save_files_count != files_count:
                save_files_count = files_count
                self.logger.debug("{} contains {} files".format(self.args.ocr_input_folder, files_count))

    def start_input_files_thread(self):
        self.input_thread = threading.Thread(target=self.process_input_tasks, args=())
        self.input_thread.start()

    def stop_input_files_thread(self):
        self.stop_input_thread = True
        self.input_thread.join()

    def input_files_thread_is_alive(self):
        self.input_thread.is_alive()

    def delete_conversion_record(self, sha256):
        if sha256 not in self.conv_db_json['files']:
            return False
        self.modify_json_lock.acquire()
        try:
            self.logger.debug("delete_conversion_record {}".format(sha256))
            file_path = CONV_DATABASE.get_converted_file_name(sha256)
            if os.path.exists(file_path):
                self.logger.debug("delete {}".format(file_path))
                os.remove(file_path)

            file_path = CONV_DATABASE.get_input_file_name(sha256)
            if os.path.exists(file_path):
                self.logger.debug("delete {}".format(file_path))
                os.remove(file_path)

            del self.conv_db_json['files'][sha256]
            self.save_json()
        finally:
            self.modify_json_lock.release()
        return True


CONV_DATABASE = None
ALLOWED_FILE_EXTENSTIONS={'.pdf'}

class THttpServer(http.server.BaseHTTPRequestHandler):

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
        global CONV_DATABASE
        CONV_DATABASE.logger.debug(msg_format % args)

    def process_special_commands(self):
        global CONV_DATABASE
        if self.path == "/ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"yes")
            return True
        if self.path == "/stat":
            self.send_response(200)
            self.end_headers()
            stats = json.dumps(CONV_DATABASE.get_stats())
            self.wfile.write(stats.encode("utf8"))
            return True
        return False

    def do_GET(self):
        def send_error(message):
            http.server.SimpleHTTPRequestHandler.send_error(self, 404, message)

        global CONV_DATABASE
        CONV_DATABASE.input_files_thread_is_alive()
        CONV_DATABASE.logger.debug(self.path)
        if self.process_special_commands():
            return

        query_components = dict()
        if not self.parse_cgi(query_components):
            send_error('bad request')
            return

        sha256 = query_components.get('sha256', None)
        if not sha256:
            send_error('No SHA256 provided')
            return

        file_path = CONV_DATABASE.get_converted_file_name(sha256)
        if file_path is None:
            send_error('File not found')
            return
        if not os.path.exists(file_path):
            send_error("Converted file does not exist")
            return
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            self.end_headers()
            if query_components.get("download_converted_file", True):
                with open(file_path, 'rb') as fh:
                    self.wfile.write(fh.read())  # Read the file and send the contents
        except Exception as exp:
            send_error(str(exp))

    def do_PUT(self):
        def send_error(message):
            http.server.SimpleHTTPRequestHandler.send_error(self, 404, message)
        global CONV_DATABASE, ALLOWED_FILE_EXTENSTIONS
        CONV_DATABASE.input_files_thread_is_alive()
        if self.path is None:
            send_error("no file specified")
            return
        action = os.path.dirname(self.path)
        _, file_extension = os.path.splitext(os.path.basename(self.path))
        action = action.strip('//')
        if action == "convert_if_absent":
            rebuild = False
        elif action == "convert_mandatory":
            rebuild = True
        else:
            send_error("bad action (file path), can be 'convert_mandatory' or 'convert_if_absent', got \"{}\"".format(action))
            return
        if file_extension not in ALLOWED_FILE_EXTENSTIONS:
            send_error("bad file extension, can be {}".format(ALLOWED_FILE_EXTENSTIONS))
            return
        file_length = int(self.headers['Content-Length'])
        max_file_size = 2**25
        if file_length > max_file_size:
            send_error("file is too large (size must less than {} bytes ".format(max_file_size))
            return
        CONV_DATABASE.logger.debug("receive file {} length {}".format(self.path, file_length))
        file_bytes = self.rfile.read(file_length)
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        if rebuild:
            CONV_DATABASE.delete_conversion_record(sha256)
        else:
            if CONV_DATABASE.get_converted_file_name(sha256):
                self.send_response(201, 'Already exists')
                self.end_headers()
                return
        if not CONV_DATABASE.save_new_file(sha256, file_bytes,  file_extension):
            self.send_response(201, 'Already registered as a conversion task, wait ')
            self.end_headers()
            return

        CONV_DATABASE.all_put_files_count += 1

        self.send_response(201, 'Created')
        self.end_headers()
        #reply_body = 'Saved file {} (file length={})\n'.format(self.path, file_length)
        #self.wfile.write(reply_body.encode('utf-8'))


if __name__ == '__main__':
    assert shutil.which("qpdf") is not None # sudo apt install qpdf
    assert shutil.which("pdfcrack") is not None #https://sourceforge.net/projects/pdfcrack/files/

    args = parse_args()
    if args.server_address is None:
        args.server_address = os.environ['DECLARATOR_CONV_URL']
    logger = logging.getLogger("db_conv_logger")
    setup_logging(logger, args.logfile)

    CONV_DATABASE = TConvDatabase(args)
    CONV_DATABASE.create_folders()
    CONV_DATABASE.start_input_files_thread()

    host, port = args.server_address.split(":")
    logger.debug("start server {}:{}".format(host, port))
    try:
        myServer = http.server.HTTPServer((host, int(port)), THttpServer)
        myServer.serve_forever()
        myServer.server_close()
    except KeyboardInterrupt as exp:
        print("ctrl+c received, exception: {}".format(exp))
        CONV_DATABASE.stop_input_files_thread()
        sys.exit(1)