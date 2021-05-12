from ConvStorage.conv_storage_server import TConvertProcessor
from ConvStorage.convert_storage import TConvertStorage
from ConvStorage.conversion_client import TDocConversionClient
from common.logging_wrapper import close_logger, setup_logging

from unittest import TestCase
import os
import threading
import shutil
import time
import subprocess


def start_server(server):
    server.start_http_server()


def find_abbyy_process():
    os.system("tasklist > tasklist.txt")
    with open ("tasklist.txt", "r") as inp:
        for l in inp:
            if 'HotFolder' in l:
                return True
    os.unlink("tasklist.txt")
    return False


def recreate_folder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=False)
    os.mkdir(folder)


def clear_folder(folder):
    for f in os.listdir(folder):
        os.unlink(os.path.join(folder, f))


class TTestEnv:
    def __init__(self, name, addit_server_args=list(), start_process=False):
        self.port = 8081
        self.name = name
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.{}".format(name))
        self.server_address = "localhost:{}".format(self.port)
        self.server = None
        self.server_thread = None
        self.server_process = None
        self.client = None
        self.pdf_ocr_folder = os.path.join(os.path.dirname(__file__), "pdf.ocr")
        self.pdf_ocr_out_folder = os.path.join(os.path.dirname(__file__), "pdf.ocr.out")
        if not os.path.exists(self.pdf_ocr_folder) or not os.path.exists(self.pdf_ocr_out_folder):
            raise Exception("run python update_finereader_task.py, and upload test.hft to finreader hot folder")
        assert (find_abbyy_process())
        self.project_file = "converted_file_storage.json"
        self.client = None
        self.server_args = None

        self.setUpServer(addit_server_args, start_process)

    def start_server_thread(self):
        self.server = TConvertProcessor(TConvertProcessor.parse_args(self.server_args))
        self.server_thread = threading.Thread(target=start_server, args=(self.server,))
        self.server_thread.start()

    def setUpServer(self, addit_server_args, start_process):
        recreate_folder(self.data_folder)

        os.chdir(self.data_folder)
        input_files = "input_files"
        recreate_folder(input_files)

        db_converted_files = os.path.join(self.data_folder, "db_converted_files")
        recreate_folder(db_converted_files)

        db_input_files = os.path.join(self.data_folder, "db_input_files")
        recreate_folder(db_input_files)

        log_file = "db_conv.log"
        if os.path.exists(log_file):
            os.unlink(log_file)

        clear_folder(self.pdf_ocr_folder)
        clear_folder(self.pdf_ocr_out_folder)
        TConvertStorage.create_empty_db(db_input_files, db_converted_files, self.project_file)

        self.server_args = [
            "--server-address", self.server_address,
            '--logfile', log_file,
            '--db-json', self.project_file,
            '--disable-killing-winword',
            '--ocr-input-folder', self.pdf_ocr_folder,
            '--ocr-output-folder', self.pdf_ocr_out_folder,
            '--disable-telegram'
        ] + addit_server_args

        if start_process:
            args = ["python", '../../conv_storage_server.py'] + self.server_args
            self.server_process = subprocess.Popen(args, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        else:
            self.start_server_thread()

    def restart_server(self):
        self.server.stop_http_server()
        self.server_thread.join(0)
        self.start_server_thread()

    def process_with_client(self, input_files, timeout=None, rebuild=False):
        output_files = list(os.path.basename(i) + ".docx" for i in input_files)
        for o in output_files:
            if os.path.exists(o):
                os.unlink(o)
        client_args = [
            "--server-address", self.server_address,
            "--conversion-timeout", "180",
            "--output-folder", ".",
        ] + input_files
        if timeout is not None:
            client_args.extend(['--conversion-timeout', str(timeout)])
        if rebuild:
            client_args.append('--rebuild')
        if self.server is None:
            logger = setup_logging(log_file_name="client.log", logger_name="db_conv_logger")
        else:
            logger = self.server.logger

        self.client = TDocConversionClient(TDocConversionClient.parse_args(client_args), logger=logger)
        self.client.start_conversion_thread()
        self.client.process_files()

        if self.server is None:
            close_logger(logger)

        return output_files

    def tearDown(self):
        if self.server is not None:
            self.server.stop_http_server()
            self.server_thread.join(0)
        else:
            self.server_process.terminate()

        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.chdir( os.path.dirname(__file__))


class TestPing(TestCase):
    def setUp(self):
        self.env = TTestEnv("ping")

    def tearDown(self):
        self.env.tearDown()

    def test_ping(self):
        cmd = "curl -s -w '%{{http_code}}'  {}/ping --output dummy.txt >http_code.txt".format(self.env.server_address)
        exit_code = os.system(cmd)
        self.assertEqual(exit_code, 0)

        with open ("http_code.txt") as inp:
            self.assertEqual(inp.read().strip(" \r\n\r'"), "200")

        with open ("dummy.txt") as inp:
            self.assertEqual(inp.read().strip(), "yes")


class TestConvWinword(TestCase):
    def setUp(self):
        self.env = TTestEnv("conv_winword", ['--disable-ocr'])

    def tearDown(self):
        self.env.tearDown()

    def test_winword(self):
        input_file = "../files/1501.pdf"
        output_file = self.env.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        file_size = os.stat(output_file).st_size

        # one more time, now without winword, since file was cached
        output_file = self.env.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        self.assertEqual(os.stat(output_file).st_size, file_size)
        stats = self.env.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 1)

        self.env.restart_server()
        output_file = self.env.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        self.assertEqual(os.stat(output_file).st_size, file_size)

        stats = self.env.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 0)


class TestOcr(TestCase):
    def setUp(self):
        self.env = TTestEnv("conv_ocr")

    def tearDown(self):
        self.env.tearDown()

    def test_ocr(self):
        output_file = self.env.process_with_client(["../files/for_ocr.pdf"])[0]
        self.assertTrue(os.path.exists(output_file))
        stats = self.env.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 1)
        self.assertEqual(stats["processed_files_size"], 24448)
        self.assertEqual(stats["is_converting"], False)


class TestBrokenPdf(TestCase):
    def setUp(self):
        self.env = TTestEnv("broken_pdf")

    def tearDown(self):
        self.env.tearDown()

    def test_broken(self):
        #files without pdf header would not be sent to the server
        output_file = self.env.process_with_client(["../files/broken.pdf"])[0]
        self.assertFalse(os.path.exists(output_file))

        stats = self.env.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 0)


class TestClientTimeout(TestCase):
    def setUp(self):
        self.env = TTestEnv("client_timeout")

    def tearDown(self):
        self.env.tearDown()

    def test_timeout(self):
        output_file = self.env.process_with_client(["../files/1501.pdf"], timeout=1)[0]
        self.assertFalse(os.path.exists(output_file))
        time.sleep(1)
        stats = self.env.server.get_stats()

        #the task was sent but the result would not retrieved because of timeout
        self.assertEqual(stats["all_put_files_count"], 1)


class TestBadAndGood(TestCase):
    def setUp(self):
        self.env = TTestEnv("bad_and_good")

    def tearDown(self):
        self.env.tearDown()

    # report pdf error from server
    def test_bad_and_good(self):
        output_files = self.env.process_with_client(["../files/good.pdf", "../files/bad.pdf"], timeout=240)
        self.assertTrue(os.path.exists(output_files[0]))
        self.assertFalse(os.path.exists(output_files[1]))
        stats = self.env.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 2)
        self.assertEqual(stats["processed_files_size"], 540269)
        self.assertEqual(stats["failed_files_size"], 531)


class TestComplicatedPdf(TestCase):
    def setUp(self):
        self.env = TTestEnv("complicated")

    def tearDown(self):
        self.env.tearDown()

    # the size of the output file must be less than 15000 (from Finereader), winword converts it to a chinese doc"
    def test_complicated_pdf(self):
        output_files = self.env.process_with_client(["../files/complicated.pdf"], timeout=240)
        self.assertTrue(os.path.exists(output_files[0]))
        file_size = os.stat(output_files[0]).st_size
        self.assertLess(file_size, 15000)


class TestWinwordConvertToJpg(TestCase):
    def setUp(self):
        # each docement to a separate bin file
        self.env = TTestEnv("prevent_word_to_jpg", addit_server_args=['--bin-file-size', '1000'])

    def tearDown(self):
        self.env.tearDown()

    def test_winword_convert_to_jpg(self):
        input_files = []
        for l in os.listdir('../files'):
            if l.startswith("4"):
                input_files.append(os.path.join('../files', l))
        input_files.append('../files/18822_cut.pdf')
        output_files = self.env.process_with_client(input_files, timeout=240)
        self.assertEqual(len(output_files), len(input_files))
        stats = self.env.server.get_stats()
        self.assertEqual(stats['finished_ocr_tasks'], len(input_files))
        file_sizes = list(os.stat(x).st_size for x in output_files)
        self.env.restart_server()
        output_files = self.env.process_with_client(input_files, timeout=240)
        new_file_sizes = list(os.stat(x).st_size for x in output_files)
        self.assertListEqual(file_sizes, new_file_sizes)


class TestRebuild(TestCase):
    def setUp(self):
        self.env = TTestEnv("rebuild", ['--disable-ocr'])

    def tearDown(self):
        self.env.tearDown()

    def test_rebuild(self):
        input_files = ['../files/1501.pdf']
        output_files = self.env.process_with_client(input_files, timeout=240)
        output_files = self.env.process_with_client(input_files, timeout=240)
        output_files = self.env.process_with_client(input_files, timeout=240, rebuild=True)

        stats = self.env.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 2) # the first client call and the third client call


class TestRestartOcr(TestCase):
    def setUp(self):
        self.env = TTestEnv("restart-ocr", ['--ocr-timeout',  '160s', '--disable-winword', '--ocr-restart-time', '180s'])

    def tearDown(self):
        self.env.tearDown()

    def test_restart_ocr(self):
        output_files = self.env.process_with_client(['../files/freeze.pdf'], timeout=200)
        self.assertFalse(os.path.exists(output_files[0]))

        output_files = self.env.process_with_client(['../files/for_ocr.pdf'], timeout=180)
        self.assertTrue(os.path.exists(output_files[0]), msg="cannot convert a normal file after ocr restart")
        with open('db_conv.log') as inp:
            s = inp.read()
            self.assertNotEqual(s.find('restart ocr'), -1)


class TestStalledFiles(TestCase):
    def setUp(self):
        self.env = TTestEnv("stalled_files", ['--ocr-timeout',  '5s'])

    def tearDown(self):
        self.env.tearDown()

    def test_stalled_files(self):
        output_files = self.env.process_with_client(['../files/for_ocr.pdf'], timeout=80)
        stats = self.env.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 1)
        self.assertEqual(stats["is_converting"], False)
        self.assertEqual(stats["failed_files_size"], 24448)
        input_ocr_files = os.listdir(self.env.pdf_ocr_folder)
        self.assertEqual(len(input_ocr_files), 0, msg="orphan files were not deleted")
        with open('db_conv.log') as inp:
            self.assertNotEqual(inp.read().find('delete orphan file'), -1)


class TestKillServer(TestCase):
    def setUp(self):
        self.env = TTestEnv("kill_server", start_process=True)

    def tearDown(self):
        self.env.tearDown()

    def test_kill_server(self):
        input_file = "../files/1501.pdf"
        output_file = self.env.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        file_size = os.stat(output_file).st_size

        # unexpected kill
        self.env.server_process.kill()
        time.sleep(2)

        self.env.start_server_thread()
        output_file = self.env.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        self.assertEqual(os.stat(output_file).st_size, file_size)
        stats = self.env.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 0)  # the first client call must be cached

