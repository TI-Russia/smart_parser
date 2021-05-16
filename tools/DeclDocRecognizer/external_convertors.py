from ConvStorage.conversion_client import TDocConversionClient
from common.primitives import run_with_timeout

import os
import shutil
import sys
from datetime import datetime


def find_program_on_windows(program):
    for prefix in ["C:\\Program Files", "C:\\Program Files (x86)"]:
        full_path = os.path.join(prefix, program)
        if os.path.exists(full_path):
            return full_path


def run_cmd(cmd):
    #print (cmd)
    return os.system(cmd)


class TExternalConverters:
    def __init__(self, enable_smart_parser=True, enable_calibre=True, enable_cat_doc=True, enable_xls2csv=True,
                 enable_office_2_txt=True):
        self.script_folder = os.path.dirname(os.path.realpath(__file__))
        self.office_2_txt = os.path.join(self.script_folder, '../Office2Txt/bin/Release/netcoreapp3.1/Office2Txt')
        self.smart_parser = os.path.join(self.script_folder, '../../src/bin/Release/netcoreapp3.1/smart_parser')
        if os.name == "nt":  # windows
            self.soffice = find_program_on_windows("LibreOffice\\program\\soffice.exe")
            if enable_calibre:
                self.calibre = find_program_on_windows("Calibre2\\ebook-convert.exe")
            self.office_2_txt += ".exe"
            self.smart_parser += ".exe"
        else:
            self.soffice = shutil.which('soffice')
            if enable_calibre:
                self.calibre = shutil.which('ebook-convert')

        if enable_smart_parser:
            if not os.path.exists(self.smart_parser):
                raise FileNotFoundError("cannot find {}, compile it".format(self.smart_parser))

            if os.environ.get('ASPOSE_LIC') is None:
                message = "add ASPOSE_LIC environment variable"
                raise Exception(message)

            if TDocConversionClient.DECLARATOR_CONV_URL is None:
                message = "set DECLARATOR_CONV_URL environment variable"
                raise Exception(message)

            if not os.path.exists(os.environ.get('ASPOSE_LIC')):
                message = "cannot find lic file {}, specified by environment variable ASPOSE_LIC".format(os.environ.get('ASPOSE_LIC'))
                raise Exception(message)

        if self.soffice is None or not os.path.exists(self.soffice):
            raise FileNotFoundError("cannot find soffice (libreoffice), install it")

        if enable_calibre:
            if self.calibre is None or not os.path.exists(self.calibre):
                raise FileNotFoundError("cannot find calibre, install calibre it")

        if enable_office_2_txt:
            if not os.path.exists(self.office_2_txt):
                raise FileNotFoundError("cannot find {}, compile it".format(office_2_txt))

        if enable_cat_doc:
            self.catdoc = shutil.which('catdoc')
            if self.catdoc is None or not os.path.exists(self.catdoc):
                raise FileNotFoundError("cannot find catdoc, install it")

        if enable_xls2csv:
            self.xls2csv = shutil.which('xls2csv')
            if self.xls2csv is None or not os.path.exists(self.xls2csv):
                raise FileNotFoundError("cannot find xls2csv, install it")

            if os.name == "nt":
                self.xlsx2csv = os.path.join( os.path.dirname(sys.executable), 'Scripts', 'xlsx2csv')
            else:
                self.xlsx2csv = shutil.which('xlsx2csv')
            if self.xlsx2csv is None or not os.path.exists(self.xlsx2csv):
                raise FileNotFoundError("cannot find xlsx2csv, install it")

    def run_calibre(self, inp, out):
        return run_with_timeout([self.calibre, inp, out])

    def run_office2txt(self, inp, out):
        return run_cmd("{} {} {}".format(self.office_2_txt, inp, out))

    def run_soffice(self, inp, out):
        run_with_timeout([self.soffice, '--headless', '--writer', '--convert-to', 'txt:Text (encoded):UTF8', inp])
        filename_wo_extenstion, _ = os.path.splitext(inp)
        temp_outfile = filename_wo_extenstion + ".txt"
        if not os.path.exists(temp_outfile):
            return 1
        shutil.move(temp_outfile, out)
        return 0

    def convert_to_pdf(self, inp, out):
        if os.path.exists(out):
            os.unlink(out)
        run_with_timeout([self.soffice, '--headless', '--writer', '--convert-to', 'pdf', inp])
        filename_wo_extenstion, _ = os.path.splitext(inp)
        temp_outfile = os.path.basename(filename_wo_extenstion + ".pdf")
        if not os.path.exists(temp_outfile):
            return 1
        shutil.move(temp_outfile, out)

    def convert_to_html_with_soffice(self, inp):
        run_with_timeout([self.soffice, '--headless', '--convert-to', 'html', inp])
        filename_wo_extenstion, _ = os.path.splitext(inp)
        temp_outfile = filename_wo_extenstion + ".html"
        if not os.path.exists(temp_outfile):
            return None
        with open(temp_outfile, encoding="utf8") as inp:
            html = inp.read()
        os.unlink(temp_outfile)
        return html

    def run_xlsx2csv(self, inp, out):
        return run_cmd("python3 \"{}\" -c utf-8 -d tab {} {}".format(self.xlsx2csv, inp, out))

    def run_xls2csv(self, inp, out):
        return run_cmd("{} -q 0 -c ' ' -d utf-8 {} > {}".format(self.xls2csv, inp, out))

    def run_catdoc(self, inp, out):
        return run_cmd("{} -d utf-8 {} > {}".format(self.catdoc, inp, out))

    def run_smart_parser_short(self, inp):
        cmd = "{} -disclosures -converted-storage-url {} -skip-relative-orphan -skip-logging -adapter prod -fio-only {}".format(
            self.smart_parser,
            TDocConversionClient.DECLARATOR_CONV_URL,
            inp)
        exit_code = run_cmd(cmd)
        #run_cmd("rm -f main.txt second.txt smart_parser*log {}.log".format(inp))
        return exit_code

    def run_smart_parser_full(self, inp, logger):
        cmd = "/usr/bin/timeout 30m {} -disclosures -decimal-raw-normalization -skip-logging -converted-storage-url {} {}".format(
            self.smart_parser,
            TDocConversionClient.DECLARATOR_CONV_URL,
            inp)
        exit_code = run_cmd(cmd)
        #run_cmd("rm -f main.txt second.txt smart_parser*log {}.log".format(inp))
        return exit_code

    def get_smart_parser_version(self):
        tmp_file = "version.tmp"
        cmd = "{} -version > {}".format(self.smart_parser, tmp_file)
        run_cmd(cmd)
        version = None
        if os.path.exists(tmp_file):
            with open(tmp_file, "r") as inp:
                version = inp.read()
                version = version.strip()
            os.unlink(tmp_file)
        return version

    def build_random_pdf(self, out_pdf_path, cnt=1):
        txt_file = out_pdf_path + ".txt"
        with open(txt_file, "w") as outp:
            for i in range(cnt):
                outp.write(str(datetime.now()) + "\n")
        self.convert_to_pdf(txt_file, out_pdf_path)
        if  not os.path.exists(out_pdf_path):
            raise Exception("cannot generate random pdf {} out of {}".format(out_pdf_path, txt_file))

    def run_smart_parser_official(self, file_path, logger=None, default_value=None):
        try:
            if logger is not None:
                logger.debug("process {} with smart_parser".format(file_path))
            self.run_smart_parser_full(file_path, logger)
            smart_parser_json = file_path + ".json"
            json_data = default_value
            if os.path.exists(smart_parser_json):
                with open(smart_parser_json, "rb") as inp:
                    json_data = inp.read()
                os.unlink(smart_parser_json)
            sha256, _ = os.path.splitext(os.path.basename(file_path))
            if logger is not None:
                logger.debug("remove file {}".format(file_path))
            os.unlink(file_path)
            return sha256, json_data
        except Exception as exp:
            if logger is not None:
                logger.error("Exception in run_smart_parser_thread:{}".format(exp))
            raise

EXTERNAl_CONVERTORS = TExternalConverters()