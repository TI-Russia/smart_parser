import argparse
import json
import time
import http.server
import os
import urllib
import hashlib
import _thread
import shutil
import subprocess
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", dest='port', default='8080', type=int)
    parser.add_argument("--server-ip", dest='server_ip', default='localhost')
    parser.add_argument("--logfile", dest='logfile', default='db_conv.log')
    parser.add_argument("--db-json", dest='db_json', required=True)
    parser.add_argument("--input-folder", dest='input_folder', required=False, default="input_files")
    parser.add_argument("--input-folder-cracked", dest='input_folder_cracked', required=False, default="input_files_cracked")
    parser.add_argument("--ocr-input-folder", dest='ocr_input_folder', required=False, default="pfd.ocr")
    parser.add_argument("--ocr-output-folder", dest='ocr_output_folder', required=False, default="pfd.ocr.out")
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


class TConvDatabase:
    def __init__(self, args):
        self.args = args
        self.conv_db_json_file_name = os.path.dirname(args.db_json)
        self.input_folder = args.input_folder
        if not os.path.exists(self.input_folder):
            os.mkdir(self.input_folder)
        with open(args.db_json, "r", encoding="utf8") as inp:
            self.conv_db_json = json.load(inp)
        self.converted_files_folder = self.conv_db_json['directory']
        assert "files" in self.conv_db_json

    def get_converted_file_name(self, sha256):
        value = self.conv_db_json['files'].get(sha256)
        if value is not None:
            return os.path.join(self.converted_files_folder, value["converted"])
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
        return True


CONV_DATABASE = None


class THttpServer(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        def send_error(message):
            http.server.SimpleHTTPRequestHandler.send_error(self, 404, message)

        global CONV_DATABASE
        query = urllib.parse.urlparse(self.path).query
        query_components = dict(qc.split("=") for qc in query.split("&"))
        sha256 = query_components.get('sha256', None)
        if not sha256:
            send_error('No SHA256 provided')
            return

        file_path = CONV_DATABASE.get_converted_file_name(sha256)
        if file_path is not None:
            if not os.path.exists(file_path):
                send_error("Converted file does not exist")
                return

            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            self.end_headers()
            if query_components.get("download_converted_file", True):
                with open(file_path, 'rb') as fh:
                    self.wfile.write(fh.read())  # Read the file and send the contents
        else:
            send_error('File not found')

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
        file_length = int(self.headers['Content-Length'])
        file_bytes = self.rfile.read(file_length)
        if not CONV_DATABASE.save_new_file(file_bytes,  file_extension):
            send_error("file already exists")
            return

        self.send_response(201, 'Created')
        self.end_headers()
        reply_body = 'Saved "%s"\n' % self.path
        self.wfile.write(reply_body.encode('utf-8'))


def check_pdf_has_text(logger, filename):
    cmd = "pdftotext {0} dummy.txt".format(filename)
    logger.info(cmd)
    os.system(cmd)
    return os.path.getsize("dummy.txt") > 200

def strip_drm(logger, filename, stripped_file):
    cmd = "pdfcrack {0} > crack.info".format(filename)
    logger.debug(cmd )
    os.system(cmd)
    password = None
    with open("crack.info", "r") as log:
        prefix = "found user-password: "
        for l in log:
            if l.startswith(prefix):
                password = prefix[len(prefix):].strip("'");
    if password is not  None:
        logger.debug( "use password {0}".format(password))
        cmd = "qpdf --password={0} --decrypt {1} {2}".format(password, filename, stripped_file)
        logger.debug (cmd)
        os.system(cmd)
        return True
    return False


def convert_with_microsoft_word(microsoft_pdf_2_docx, filename):
    subprocess.run([microsoft_pdf_2_docx, filename], timeout=60*10)
    os.system("taskkill /F /IM  winword.exe")
    os.system("taskkill /F /IM  pdfreflow.exe")


def process_one_input_file(args, conv_database, some_file):
    logger = logging.getLogger("db_conv_logger")
    stripped_file = os.path.join(args.input_folder_cracked, some_file)
    input_file = os.path.join(args.input_folder, some_file)
    logger.debug("pwd={}".format(os.getcwd()))
    if not strip_drm(logger, input_file, stripped_file):
        shutil.copyfile(input_file, stripped_file)
    if check_pdf_has_text(logger, stripped_file):
        logger.info("convert {} with microsoft word".format(input_file))
        convert_with_microsoft_word(args.microsoft_pdf_2_docx, stripped_file)
        docxfile = stripped_file + ".docx"
        if not os.path.exists(docxfile):
            logger.info("cannot process {}, delete it".format(some_file))
            os.unlink(input_file)
            os.unlink(stripped_file)
        else:
            logger.info(
                "move {} and {} to {}".format(input_file, docxfile, conv_database.converted_files_folder))
            shutil.move(docxfile, os.path.join(conv_database.converted_files_folder, some_file + ".docx"))
            shutil.move(input_file, os.path.join(conv_database.converted_files_folder, some_file))
            os.unlink(stripped_file)
    else:
        logger.info("move {} to {}".format(stripped_file, args.ocr_input_folder))
        shutil.move(stripped_file, os.path.join(args.ocr_input_folder, some_file))
        shutil.move(input_file, os.path.join(conv_database.converted_files_folder, some_file))



def move_one_ocred_file(args, conv_database, some_file):
    logger = logging.getLogger("db_conv_logger")
    assert some_file.endswith(".docx")
    pdf_file = some_file[:-len(".docx")]
    assert os.path.exists(os.path.join(conv_database.converted_files_folder, pdf_file))

    input_ocr_file = os.path.join(args.ocr_input_folder, pdf_file)
    assert os.path.exists( input_ocr_file )
    logger.debug("delete {}".format(input_ocr_file))
    os.unlink(input_ocr_file)

    f1 = os.path.join(args.ocr_output_folder, some_file)
    f2 = os.path.join(conv_database.converted_files_folder, some_file)
    logger.debug("move  {} to {}".format(f1, f2))
    shutil.move(f1, f2)


def process_input_files(args, conv_database):
    logger = logging.getLogger("db_conv_logger")
    logger.debug("use {} as  microsoft word converter".format(args.microsoft_pdf_2_docx))
    assert os.path.exists(args.microsoft_pdf_2_docx)
    if os.path.exists(args.input_folder_cracked):
        shutil.rmtree(args.input_folder_cracked)
    if not os.path.exists(args.input_folder_cracked):
        logger.debug("mkdir {} ".format(args.input_folder_cracked))
        os.mkdir(args.input_folder_cracked)
    while True:
        time.sleep(1)
        updated = False
        for some_file in os.listdir(args.input_folder):
            try:
                process_one_input_file(args, conv_database, some_file)
                updated = True
            except Exception as exp:
                fname = os.path.join(args.input_folder, some_file)
                if os.path.exists(fname):
                    logger.error("Exception {}, delete {}".format(exp, some_file))
                    os.unlink(fname)

        for some_file in os.listdir(args.ocr_output_folder):
            for try_index in [1, 2, 3]:
                try:
                    if some_file.endswith(".docx"):
                        move_one_ocred_file(args, conv_database, some_file)
                        updated = True
                except Exception as exp:
                    if try_index == 3:
                        full_path = os.path.join(args.ocr_output_folder, some_file)
                        if os.path.exists(full_path):
                            logger.error("Exception {}, delete {}".format(exp, full_path))
                            os.unlink(full_path)
                    else:
                        time.sleep(30)
        if updated:
            rebuild_json(conv_database.conv_db_json,
                         conv_database.converted_files_folder,
                         conv_database.conv_db_json_file_name)

if __name__ == '__main__':
    assert shutil.which("qpdf") is not None # sudo apt install qpdf
    assert shutil.which("pdfcrack") is not None #https://sourceforge.net/projects/pdfcrack/files/
    assert shutil.which("pdftotext") is not None #http://www.xpdfreader.com/download.html

    args = parse_args()
    logger = logging.getLogger("db_conv_logger")
    setup_logging(logger, args.logfile)
    if not os.path.exists(args.ocr_input_folder):
        os.mkdir(args.ocr_input_folder)
    if not os.path.exists(args.ocr_output_folder):
        os.mkdir(args.ocr_output_folder)

    CONV_DATABASE = TConvDatabase(args)
    _thread.start_new_thread(process_input_files, (args, CONV_DATABASE))


    myServer = http.server.HTTPServer((args.server_ip, args.port), THttpServer)
    myServer.serve_forever()
    myServer.server_close()
