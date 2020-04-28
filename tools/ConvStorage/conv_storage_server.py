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
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)


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
    cmd = "pdfcrack {0} > crack.info".format(filename)
    logger.debug(cmd )
    os.system(cmd)
    password = None
    with open("crack.info", "r") as log:
        prefix = "found user-password: "
        for l in log:
            if l.startswith(prefix):
                password = prefix[len(prefix):].strip("'")
    os.unlink("crack.info")
    if password is not None:
        logger.debug("use password {0}".format(password))
        cmd = "qpdf --password={0} --decrypt {1} {2}".format(password, filename, stripped_file)
        logger.debug (cmd)
        os.system(cmd)
        return True
    return False


def convert_with_microsoft_word(microsoft_pdf_2_docx, filename):
    subprocess.run([microsoft_pdf_2_docx, filename], timeout=60*10)
    os.system("taskkill /F /IM  winword.exe")
    os.system("taskkill /F /IM  pdfreflow.exe")


def delete_file_if_exists(logger, full_path):
    try:
        if os.path.exists(full_path):
            logger.debug("delete {}".format(full_path))
            os.unlink(full_path)
    except Exception as exp:
        logger.error("Exception {}, cannot delete {}, do not know how to deal with it...".format(exp, full_path))


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

    def save_new_file(self, file_bytes, file_extension):
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        if self.get_converted_file_name(sha256):
            return False
        filename = os.path.join(self.input_folder, sha256 + file_extension)
        if os.path.exists(filename):
            return False
        with open(filename, 'wb') as output_file:
            output_file.write(file_bytes)
        self.logger.debug("save new file {} ".format(filename))
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

    def process_one_input_file(self, some_file):
        stripped_file = os.path.join(self.args.input_folder_cracked, some_file)
        input_file = os.path.join(self.args.input_folder, some_file)
        self.logger.debug("process input file {}, pwd={}".format(input_file, os.getcwd()))
        if not strip_drm(self.logger, input_file, stripped_file):
            shutil.copyfile(input_file, stripped_file)
        if not self.args.enable_ocr or check_pdf_has_text(self.logger, stripped_file):
            self.logger.info("convert {} with microsoft word".format(input_file))
            convert_with_microsoft_word(self.args.microsoft_pdf_2_docx, stripped_file)
            docxfile = stripped_file + ".docx"
            if not os.path.exists(docxfile):
                self.logger.info("cannot process {}, delete it".format(some_file))
                os.unlink(input_file)
                os.unlink(stripped_file)
            else:
                self.logger.info(
                    "move {} and {} to {}".format(input_file, docxfile, self.converted_files_folder))
                shutil.move(docxfile, os.path.join(self.converted_files_folder, some_file + ".docx"))
                shutil.move(input_file, os.path.join(self.converted_files_folder, some_file))
                os.unlink(stripped_file)
        else:
            self.logger.info("move {} to {}".format(stripped_file, self.args.ocr_input_folder))
            shutil.move(stripped_file, os.path.join(self.args.ocr_input_folder, some_file))
            shutil.move(input_file, os.path.join(self.converted_files_folder, some_file))

    def create_folders(self):
        self.logger.debug("use {} as  microsoft word converter".format(self.args.microsoft_pdf_2_docx))
        self.logger.debug("input folder for new files: {} ".format(self.args.input_folder))
        if not os.path.exists(self.args.ocr_input_folder):
            os.mkdir(self.args.ocr_input_folder)
        if not os.path.exists(self.args.ocr_output_folder):
            os.mkdir(self.args.ocr_output_folder)
        if not os.path.exists(self.input_folder):
            os.mkdir(self.input_folder)

        assert os.path.exists(self.args.microsoft_pdf_2_docx)
        self.args.input_folder_cracked = tempfile.mkdtemp(prefix="input_files_cracked", dir=".")

    def rebuild_json_wrapper(self):
        self.logger.info("rebuild json started, files number={}".format(len(self.conv_db_json["files"])))
        rebuild_json(self.conv_db_json,
                     self.converted_files_folder,
                     self.conv_db_json_file_name)
        self.logger.info("rebuild json finished, files number={}".format(len(self.conv_db_json["files"])))

    def process_input_files(self):
        while not self.stop_input_thread:
            time.sleep(10)

            input_files = list(os.listdir(self.args.input_folder))
            if len(input_files) > 0:
                self.logger.debug("the input folder contains {} unprocessed files".format(len(input_files)))

            updated = False
            for some_file in input_files:
                try:
                    self.process_one_input_file(some_file)
                    updated = True
                except Exception as exp:
                    self.logger.error("Exception: {}".format(exp))
                    fname = os.path.join(self.args.input_folder, some_file)
                    if os.path.exists(fname):
                        self.logger.error("delete {}".format(fname))
                        os.unlink(fname)

            for some_file in os.listdir(self.args.ocr_output_folder):
                if not some_file.endswith(".docx"):
                    continue
                for try_index in [1, 2, 3]:
                    self.logger.info("got file {} from finereader try to move it, trial No {}".format(some_file, try_index))
                    try:
                        self.move_one_ocred_file(some_file)
                        updated = True
                        break
                    except Exception as exp:
                        self.logger.error("Exception {}, sleep 60 seconds ...".format(str(exp)))
                        time.sleep(60)

                delete_file_if_exists(logger, os.path.join(args.ocr_output_folder, some_file))

            if updated:
                self.rebuild_json_wrapper()

    def start_input_files_thread(self):
        self.input_thread = threading.Thread(target=self.process_input_files, args=())
        self.input_thread.start()

    def stop_input_files_thread(self):
        self.stop_input_thread = True
        self.input_thread.join()

CONV_DATABASE = None


class THttpServer(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        def send_error(message):
            http.server.SimpleHTTPRequestHandler.send_error(self, 404, message)

        global CONV_DATABASE
        CONV_DATABASE.logger.debug(self.path)
        if self.path == "/ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"yes")
            return
        query = urllib.parse.urlparse(self.path).query

        query_components = dict()
        for qc in query.split("&"):
            items = qc.split("=")
            if len(items) != 2:
                send_error('bad request')
                return
            query_components[items[0]] = items[1]   

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
            if query_components.get('delete_file') is not None:
                CONV_DATABASE.logger.debug("delete {}".format(file_path))
                os.remove(file_path)

                file_path = CONV_DATABASE.get_input_file_name(sha256)
                if os.path.exists(file_path):
                    CONV_DATABASE.logger.debug("delete {}".format(file_path))
                    os.remove(file_path)
                CONV_DATABASE.rebuild_json_wrapper()
                self.send_response(200)
            else:
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
        if self.path is None:
            send_error("no file specified")
            return
        file_extension = os.path.splitext(self.path)[1]
        if len(file_extension) <= 3:
            send_error("bad file extension")
            return
        CONV_DATABASE.logger.debug(self.path)
        file_length = int(self.headers['Content-Length'])
        file_bytes = self.rfile.read(file_length)
        if not CONV_DATABASE.save_new_file(file_bytes,  file_extension):
            send_error("file already exists")
            return

        self.send_response(201, 'Created')
        self.end_headers()
        reply_body = 'Saved "%s"\n' % self.path
        self.wfile.write(reply_body.encode('utf-8'))


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
    except KeyboardInterrupt:
        print("ctrl+c received")
        CONV_DATABASE.stop_input_files_thread()
        sys.exit(1)