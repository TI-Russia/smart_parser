import argparse
import json
import time
import http.server
import os
import urllib
import hashlib
import shutil
import subprocess
import logging
import threading
import tempfile
import sys
import queue


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-address", dest='server_address', default=None, help="by default read it from environment variable DECLARATOR_CONV_URL")
    parser.add_argument("--logfile", dest='logfile', default='db_conv.log')
    parser.add_argument("--db-json", dest='db_json', required=True)
    parser.add_argument("--disable-ocr", dest='enable_ocr', default=True, required=False, action="store_false")
    parser.add_argument("--input-folder", dest='input_folder', required=False, default="input_files")
    parser.add_argument("--input-folder-cracked", dest='input_folder_cracked', required=False, default="input_files_cracked")
    parser.add_argument("--ocr-input-folder", dest='ocr_input_folder', required=False, default="pdf.ocr")
    parser.add_argument("--ocr-output-folder", dest='ocr_output_folder', required=False, default="pdf.ocr.out")
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


def rebuild_json(conv_db_json, converted_files_folder, output_file):
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


def check_pdf_has_text(logger, filename):
    cmd = "pdftotext {0} dummy.txt 2> pdftotext.log".format(filename)
    logger.info(cmd)
    os.system(cmd)
    with open("pdftotext.log", "r") as inpf:
        log = inpf.read()
    os.unlink("pdftotext.log")
    if log.find("PDF file is damaged") != -1:
        return False  # complicated_pdf in  tests
    is_good_text = os.path.getsize("dummy.txt") > 200
    os.unlink("dummy.txt")
    return is_good_text


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
    def __init__(self, file_path, sha256,  rebuild):
        self.file_path = file_path
        self.sha256 = sha256
        self.rebuild = rebuild


class TConvDatabase:
    def __init__(self, args):
        self.args = args
        self.conv_db_json_file_name = args.db_json
        self.input_folder = args.input_folder
        with open(args.db_json, "r", encoding="utf8") as inp:
            self.conv_db_json = json.load(inp)
        self.converted_files_folder = self.conv_db_json['directory']
        assert "files" in self.conv_db_json
        self.logger = logging.getLogger("db_conv_logger")
        self.input_thread = None
        self.stop_input_thread = False
        self.input_task_queue = queue.Queue()

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

    def save_new_file(self, sha256, file_bytes, file_extension, rebuild):
        filename = os.path.join(self.input_folder, sha256 + file_extension)
        if os.path.exists(filename): #already registered as an input task
            return False
        with open(filename, 'wb') as output_file:
            output_file.write(file_bytes)
        self.logger.debug("save new file {} ".format(filename))
        task = TInputTask(filename, sha256, rebuild)
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
        if not self.args.enable_ocr or check_pdf_has_text(self.logger, stripped_file):
            self.logger.info("convert {} with microsoft word".format(input_file))
            convert_with_microsoft_word(self.logger, self.args.microsoft_pdf_2_docx, stripped_file)
            docxfile = stripped_file + ".docx"
            if not os.path.exists(docxfile):
                self.logger.info("cannot process {}, delete it".format(input_file))
                os.unlink(input_file)
                os.unlink(stripped_file)
            else:
                self.logger.info(
                    "move {} and {} to {}".format(input_file, docxfile, self.converted_files_folder))
                shutil.move(docxfile, os.path.join(self.converted_files_folder, basename + ".docx"))
                shutil.move(input_file, os.path.join(self.converted_files_folder, basename))
                os.unlink(stripped_file)
        else:
            self.logger.info("move {} to {}".format(stripped_file, self.args.ocr_input_folder))
            shutil.move(stripped_file, os.path.join(self.args.ocr_input_folder, basename))
            shutil.move(input_file, os.path.join(self.converted_files_folder, basename))

    def create_folders(self):
        self.logger.debug("use {} as  microsoft word converter".format(self.args.microsoft_pdf_2_docx))
        self.logger.debug("input folder for new files: {} ".format(self.args.input_folder))
        if os.path.exists(self.args.ocr_input_folder): #no way to process the input files without queue
            shutil.rmtree(self.args.ocr_input_folder, ignore_errors=True)
        if not os.path.exists(self.args.ocr_input_folder):
            os.mkdir(self.args.ocr_input_folder)
        if not os.path.exists(self.args.ocr_output_folder):
            os.mkdir(self.args.ocr_output_folder)
        if not os.path.exists(self.input_folder):
            os.mkdir(self.input_folder)
        if not os.path.exists(self.converted_files_folder):
            os.mkdir(self.converted_files_folder)

        assert os.path.exists(self.args.microsoft_pdf_2_docx)
        self.args.input_folder_cracked = tempfile.mkdtemp(prefix="input_files_cracked", dir=".")

    # can only add new files
    def rebuild_json_wrapper(self):
        self.logger.info("rebuild json started, files number={}".format(len(self.conv_db_json["files"])))
        rebuild_json(self.conv_db_json,
                     self.converted_files_folder,
                     self.conv_db_json_file_name)
        self.logger.info("rebuild json finished, files number={}".format(len(self.conv_db_json["files"])))

    def save_json(self):
        with open(self.conv_db_json_file_name, "w") as outf:
            json.dump(self.conv_db_json, outf, indent=4)

    def process_input_tasks(self):
        while not self.stop_input_thread:
            time.sleep(10)
            new_files_in_db = False
            while not self.input_task_queue.empty():
                task = self.input_task_queue.get()
                if task.rebuild:
                    self.delete_item(task.sha256)
                    self.save_json()
                try:
                    self.process_one_input_file(task.file_path)
                    new_files_in_db = True
                except Exception as exp:
                    self.logger.error("Exception: {}".format(exp))
                    if os.path.exists(task.file_path):
                        self.logger.error("delete {}".format(task.file_path))
                        os.unlink(task.file_path)

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

            if new_files_in_db:
                self.rebuild_json_wrapper()

    def start_input_files_thread(self):
        self.input_thread = threading.Thread(target=self.process_input_tasks, args=())
        self.input_thread.start()

    def stop_input_files_thread(self):
        self.stop_input_thread = True
        self.input_thread.join()

    def input_files_thread_is_alive(self):
        self.input_thread.is_alive()

    def delete_item(self, sha256):
        if sha256 not in self.conv_db_json['files']:
            return False
        self.logger.debug("delete_item {}".format(sha256))
        file_path = CONV_DATABASE.get_converted_file_name(sha256)
        if os.path.exists(file_path):
            self.logger.debug("delete {}".format(file_path))
            os.remove(file_path)

        file_path = CONV_DATABASE.get_input_file_name(sha256)
        if os.path.exists(file_path):
            self.logger.debug("delete {}".format(file_path))
            os.remove(file_path)

        del self.conv_db_json['files'][sha256]
        return True


CONV_DATABASE = None


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

    def do_GET(self):
        def send_error(message):
            http.server.SimpleHTTPRequestHandler.send_error(self, 404, message)

        global CONV_DATABASE
        CONV_DATABASE.input_files_thread_is_alive()
        CONV_DATABASE.logger.debug(self.path)
        if self.path == "/ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"yes")
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
        global CONV_DATABASE
        CONV_DATABASE.input_files_thread_is_alive()
        if self.path is None:
            send_error("no file specified")
            return
        action, file_extension = os.path.split(self.path)
        action = action.strip('//')
        if action == "convert_if_absent":
            rebuild = False
        elif action == "convert_mandatory":
            rebuild = True
        else:
            send_error("bad action (file path), can be 'convert_mandatory' or 'convert_if_absent', got \"{}\"".format(action))
            return
        if len(file_extension) <= 3:
            send_error("bad file extension")
            return
        file_length = int(self.headers['Content-Length'])
        CONV_DATABASE.logger.debug("receive file {} length {}".format(self.path, file_length))
        file_bytes = self.rfile.read(file_length)
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        if not rebuild:
            if CONV_DATABASE.get_converted_file_name(sha256):
                self.send_response(201, 'Already exists')
                self.end_headers()
                return

        if not CONV_DATABASE.save_new_file(sha256, file_bytes,  file_extension, rebuild):
            self.send_response(201, 'Already registered as a conversion task, wait ')
            self.end_headers()
            return

        self.send_response(201, 'Created')
        self.end_headers()
        #reply_body = 'Saved file {} (file length={})\n'.format(self.path, file_length)
        #self.wfile.write(reply_body.encode('utf-8'))


if __name__ == '__main__':
    assert shutil.which("qpdf") is not None # sudo apt install qpdf
    assert shutil.which("pdfcrack") is not None #https://sourceforge.net/projects/pdfcrack/files/
    assert shutil.which("pdftotext") is not None #http://www.xpdfreader.com/download.html

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