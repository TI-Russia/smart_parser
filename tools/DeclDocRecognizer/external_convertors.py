import subprocess
import os
import shutil
import sys

def find_program_on_windows(program):
    for prefix in ["C:\\Program Files", "C:\\Program Files (x86)"]:
        full_path = os.path.join(prefix, program)
        if os.path.exists(full_path):
            return full_path

def run_cmd(cmd):
    #print (cmd)
    return os.system(cmd)


def run_with_timeout(args, timeout=30*60):
    p = subprocess.Popen(args, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    try:
        p.wait(timeout)
    except subprocess.TimeoutExpired:
        p.kill()


class TExternalConverters:
    def __init__(self):
        self.script_folder = os.path.dirname(os.path.realpath(__file__))
        self.office_2_txt = os.path.join(self.script_folder, '../Office2Txt/bin/Release/netcoreapp3.1/Office2Txt')
        self.smart_parser = os.path.join(self.script_folder, '../../src/bin/Release/netcoreapp3.1/smart_parser')
        if os.name == "nt":  # windows
            self.soffice = find_program_on_windows("LibreOffice\\program\\soffice.exe")
            self.calibre = find_program_on_windows("Calibre2\\ebook-convert.exe")
            self.office_2_txt += ".exe"
            self.smart_parser += ".exe"
        else:
            self.soffice = shutil.which('soffice')
            self.calibre = shutil.which('ebook-convert')

        if not os.path.exists(self.smart_parser):
            raise FileNotFoundError("cannot find {}, compile it".format(self.smart_parser))
        if self.soffice is None or not os.path.exists(self.soffice):
            raise FileNotFoundError("cannot find soffice (libreoffice), install it")
        if self.calibre is None or not os.path.exists(self.calibre):
            raise FileNotFoundError("cannot find calibre, install calibre it")
        if not os.path.exists(self.office_2_txt):
            raise FileNotFoundError("cannot find {}, compile it".format(office_2_txt))
        self.catdoc = shutil.which('catdoc')
        if self.catdoc is None or not os.path.exists(self.catdoc):
            raise FileNotFoundError("cannot find catdoc, install it")
        self.xls2csv = shutil.which('xls2csv')
        if self.xls2csv is None or not os.path.exists(self.xls2csv):
            raise FileNotFoundError("cannot find xls2csv, install it")

        if os.name == "nt":
            self.xlsx2csv = os.path.join( os.path.dirname(sys.executable), 'Scripts', 'xlsx2csv')
        else:
            self.xlsx2csv = shutil.which('xlsx2csv')
        if self.xlsx2csv is None or not os.path.exists(self.xlsx2csv):
            raise FileNotFoundError("cannot find xlsx2csv, install it")

    smart_parser_default = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "../../src/bin/Release/netcoreapp3.1/smart_parser"
    )
    if os.name == "nt":
        smart_parser_default += ".exe"

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
        return run_cmd("python \"{}\" -c utf-8 -d tab {} {}".format(self.xlsx2csv, inp, out))

    def run_xls2csv(self, inp, out):
        return run_cmd("{} -q 0 -c ' ' -d utf-8 {} > {}".format(self.xls2csv, inp, out))

    def run_catdoc(self, inp, out):
        return run_cmd("{} -d utf-8 {} > {}".format(self.catdoc, inp, out))

EXTERNAl_CONVERTORS = TExternalConverters()