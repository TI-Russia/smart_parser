from ConvStorage.conv_storage_server import TConvertProcessor
from ConvStorage.convert_storage import TConvertStorage
from ConvStorage.conversion_client import TDocConversionClient
from common.logging_wrapper import close_logger, setup_logging
from common.primitives import build_dislosures_sha256
from DeclDocRecognizer.external_convertors import TExternalConverters

import concurrent.futures
from unittest import TestCase
import os
import threading
import shutil
import time
import subprocess
import random
from functools import partial


def start_server(server):
    server.start_http_server()


def recreate_folder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=False)
    os.mkdir(folder)

def clear_folder(folder):
    for f in os.listdir(folder):
        os.unlink(os.path.join(folder, f))


class TTestConvBase(TestCase):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.port = 8081
        self.name = None
        self.data_folder = None
        self.server_address = "localhost:{}".format(self.port)
        self.server = None
        self.server_thread = None
        self.server_process = None
        self.client = None
        self.converters = TExternalConverters(enable_smart_parser=False, enable_calibre=False, enable_cat_doc=False,
                                         enable_xls2csv=False, enable_office_2_txt=False)

        self.pdf_ocr_folder = os.path.join(os.path.dirname(__file__), "pdf.ocr")
        self.pdf_ocr_out_folder = os.path.join(os.path.dirname(__file__), "pdf.ocr.out")
        if not os.path.exists(self.pdf_ocr_folder) or not os.path.exists(self.pdf_ocr_out_folder):
            raise Exception("run python update_finereader_task.py, and upload test.hft to finreader hot folder")
        self.project_file = "converted_file_storage.json"
        self.client = None
        self.server_args = None
        self.client_count = 0;

    def start_server_thread(self):
        self.server = TConvertProcessor(TConvertProcessor.parse_args(self.server_args))
        self.server_thread = threading.Thread(target=start_server, args=(self.server,))
        self.server_thread.start()

    def setup_server(self, name, addit_server_args=list(), start_process=False):
        self.name = name
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.{}".format(name))

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
            server_script = os.path.join(os.path.dirname(__file__), "..", "conv_storage_server.py")
            args = ["python", server_script] + self.server_args
            self.server_process = subprocess.Popen(args, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        else:
            self.start_server_thread()

    def restart_server(self):
        self.server.stop_http_server()
        self.server_thread.join(0)
        self.start_server_thread()

    def process_with_client(self, input_files, timeout=None, rebuild=False, skip_receiving=False, log_name="client",
                            input_task_timeout=5):
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
        if skip_receiving:
            client_args.append('--skip-receiving')
        if self.client_count >= 0 and log_name == "client":
            log_name = log_name + str(self.client_count)
        logger = setup_logging(logger_name=log_name)
        try:
            self.client_count += 1
            self.client = TDocConversionClient(TDocConversionClient.parse_args(client_args), logger=logger)
            self.client.input_task_timeout = input_task_timeout
            self.client.start_conversion_thread()
            self.client.process_files()
            return output_files
        finally:
            close_logger(logger)


    def list2reason(self, exc_list):
        if exc_list and exc_list[-1][0] is self:
            return exc_list[-1][1]

    def tear_down(self):
        result = self.defaultTestResult()
        self._feedErrorsToResult(result, self._outcome.errors)
        error = self.list2reason(result.errors)
        failure = self.list2reason(result.failures)
        delete_temp_files = not error and not failure

        if self.client is not None:
            self.client.stop_conversion_thread(1)
            self.client = None

        if self.server is not None:
            self.server.stop_http_server()
            self.server_thread.join(0)
            self.server = None
        else:
            self.server_process.kill()
            self.server_process = None

        time.sleep(5)

        os.chdir(os.path.dirname(__file__))

        if delete_temp_files:
            for i in range(3):
                try:
                    if os.path.exists(self.data_folder):
                        shutil.rmtree(self.data_folder, ignore_errors=True)
                except Exception as e:
                    print("cannot delete {}, exception = {}".format(self.data_folder, str(e)))
                    time.sleep(10)


class TestPing(TTestConvBase):
    def setUp(self):
        self.setup_server("ping")

    def tearDown(self):
        self.tear_down()

    def test_simple_ping(self):
        cmd = "curl -s -w '%{{http_code}}'  {}/ping --output dummy.txt >http_code.txt".format(self.server_address)
        exit_code = os.system(cmd)
        self.assertEqual(exit_code, 0)
        with open ("http_code.txt") as inp:
            self.assertEqual(inp.read().strip(" \r\n\r'"), "200")

        with open ("dummy.txt") as inp:
            self.assertEqual(inp.read().strip(), "yes")


class TestConvWinword(TTestConvBase):
    def setUp(self):
        self.setup_server("conv_winword", ['--disable-ocr'])

    def tearDown(self):
        self.tear_down()

    def test_winword(self):
        input_file = "../files/1501.pdf"
        output_file = self.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        file_size = os.stat(output_file).st_size

        # one more time, now without winword, since file was cached
        output_file = self.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        self.assertEqual(os.stat(output_file).st_size, file_size)
        stats = self.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 1)

        self.restart_server()
        output_file = self.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        self.assertEqual(file_size, os.stat(output_file).st_size)

        stats = self.server.get_stats()
        self.assertEqual(0, stats["all_put_files_count"])


class TestOcr(TTestConvBase):
    def setUp(self):
        self.setup_server("conv_ocr")

    def tearDown(self):
        self.tear_down()

    def test_ocr(self):
        output_file = self.process_with_client(["../files/for_ocr.pdf"])[0]
        self.assertTrue(os.path.exists(output_file))
        stats = self.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 1)
        self.assertEqual(stats["processed_files_size"], 24448)
        self.assertEqual(stats["is_converting"], False)


class TestBrokenPdf(TTestConvBase):
    def setUp(self):
        self.setup_server("broken_pdf")

    def tearDown(self):
        self.tear_down()

    def test_broken(self):
        #files without pdf header would not be sent to the server
        output_file = self.process_with_client(["../files/broken.pdf"])[0]
        self.assertFalse(os.path.exists(output_file))

        stats = self.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 0)


class TestClientTimeout(TTestConvBase):
    def setUp(self):
        self.setup_server("client_timeout")

    def tearDown(self):
        self.tear_down()

    def test_timeout(self):
        output_file = self.process_with_client(["../files/1501.pdf"], timeout=1)[0]
        self.assertFalse(os.path.exists(output_file))
        time.sleep(1)
        stats = self.server.get_stats()

        #the task was sent but the result would not retrieved because of timeout
        self.assertEqual(stats["all_put_files_count"], 1)


class TestBadAndGood(TTestConvBase):
    def setUp(self):
        self.setup_server("bad_and_good")

    def tearDown(self):
        self.tear_down()

    # report pdf error from server
    def test_bad_and_good(self):
        files = list()
        for f in ["good.pdf", "bad.pdf"]:
            path = os.path.join(os.path.dirname(__file__), "files", f)
            assert os.path.exists(path)
            files.append(path)
        output_files = self.process_with_client(files, timeout=240)
        self.assertTrue(os.path.exists(output_files[0]))
        self.assertFalse(os.path.exists(output_files[1]))
        stats = self.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 2)
        self.assertEqual(stats["processed_files_size"], 540269)
        self.assertEqual(stats["failed_files_size"], 531)


class TestComplicatedPdf(TTestConvBase):
    def setUp(self):
        self.setup_server("complicated")

    def tearDown(self):
        self.tear_down()

    # the size of the output file must be less than 15000 (from Finereader), winword converts it to a chinese doc"
    def test_complicated_pdf(self):
        output_files = self.process_with_client(["../files/complicated.pdf"], timeout=240)
        self.assertTrue(os.path.exists(output_files[0]))
        file_size = os.stat(output_files[0]).st_size
        self.assertLess(file_size, 15000)


class TestWinwordConvertToJpg(TTestConvBase):
    def setUp(self):
        # each docement to a separate bin file
        self.setup_server("prevent_word_to_jpg", addit_server_args=['--bin-file-size', '1000'])

    def tearDown(self):
        self.tear_down()

    def test_winword_convert_to_jpg(self):
        input_files = []
        for l in os.listdir('../files'):
            if l.startswith("4"):
                input_files.append(os.path.join('../files', l))
        input_files.append('../files/18822_cut.pdf')
        canon_input_files_count = 7
        assert len(input_files) == canon_input_files_count
        output_files = self.process_with_client(input_files, timeout=240)
        self.assertEqual(canon_input_files_count, len(output_files))
        stats = self.server.get_stats()
        self.assertEqual(canon_input_files_count, stats['finished_ocr_tasks'])
        file_sizes = list(os.stat(x).st_size for x in output_files)
        self.restart_server()
        output_files = self.process_with_client(input_files, timeout=240)
        new_file_sizes = list(os.stat(x).st_size for x in output_files)
        self.assertListEqual(file_sizes, new_file_sizes)


class TestRestartOcr(TTestConvBase):
    def setUp(self):
        self.setup_server("restart_ocr")

    def tearDown(self):
        self.tear_down()

    def test_restart(self):
        # it seems that there is a problem in this test  under Pycharm because Pycharm deletes all child processes
        # after test end
        self.server.restart_ocr()
        self.assertIsNotNone(self.server.get_hot_folder_path_from_running_tasks())


class TestRebuild(TTestConvBase):
    def setUp(self):
        self.setup_server("rebuild1", ['--disable-ocr'])

    def tearDown(self):
        self.tear_down()

    def test_rebuild(self):
        input_files = ['../files/1501.pdf']
        output_files = self.process_with_client(input_files, timeout=240)
        output_files = self.process_with_client(input_files, timeout=240)
        output_files = self.process_with_client(input_files, timeout=240, rebuild=True)

        stats = self.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 2) # the first client call and the third client call


class TestRestartOcrAfterFreeze(TTestConvBase):
    def setUp(self):
        self.setup_server("restart-ocr1", ['--ocr-timeout',  '160s', '--disable-winword', '--ocr-restart-time', '180s'])

    def tearDown(self):
        self.tear_down()

    def test_restart_after_freeze(self):

        #may be we should also restart "hot folder" application
        output_files = self.process_with_client(['../files/freeze.pdf'], timeout=200)
        self.assertFalse(os.path.exists(output_files[0]))

        output_files = self.process_with_client(['../files/for_ocr.pdf'], timeout=180)
        self.assertTrue(os.path.exists(output_files[0]), msg="cannot convert a normal file after ocr restart")
        with open('db_conv.log') as inp:
            s = inp.read()
            self.assertNotEqual(-1, s.find('restart ocr'))


class TestStalledFiles(TTestConvBase):
    def setUp(self):
        self.setup_server("stalled_files", ['--ocr-timeout',  '5s'])

    def tearDown(self):
        self.tear_down()

    def test_stalled_files(self):
        output_files = self.process_with_client(['../files/for_ocr.pdf'], timeout=80)
        stats = self.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 1)
        self.assertEqual(stats["is_converting"], False)
        self.assertEqual(stats["failed_files_size"], 24448)
        input_ocr_files = os.listdir(self.pdf_ocr_folder)
        self.assertEqual(len(input_ocr_files), 0, msg="orphan files were not deleted")
        with open('db_conv.log') as inp:
            self.assertNotEqual(inp.read().find('delete orphan file'), -1)


class TestKillServer(TTestConvBase):
    def setUp(self):
        self.setup_server("kill_server", start_process=True)

    def tearDown(self):
        self.tear_down()

    def test_kill_server(self):
        input_file = "../files/1501.pdf"
        output_file = self.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        file_size = os.stat(output_file).st_size

        # unexpected kill
        self.server_process.kill()
        time.sleep(2)

        self.start_server_thread()
        output_file = self.process_with_client([input_file])[0]
        self.assertTrue(os.path.exists(output_file))
        self.assertEqual(os.stat(output_file).st_size, file_size)
        stats = self.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 0)  # the first client call must be cached


# read  from TSnowBallFileStorage.bin_files[-1] file that is open with mode a+
class TestReadFromAplusFile(TTestConvBase):
    def setUp(self):
        self.setup_server("read_from_aplus_file")

    def tearDown(self):
        self.tear_down()

    def write_and_read(self, file_name):
        # write to  storage a new file
        output_file = self.process_with_client([file_name])[0]
        self.assertTrue(os.path.exists(output_file))
        file_size = os.stat(output_file).st_size
        hash_code = build_dislosures_sha256(output_file)

        # read  file
        os.unlink(output_file)
        output_file_copy = self.process_with_client([file_name])[0]
        self.assertTrue(os.path.exists(output_file_copy))
        self.assertEqual(os.stat(output_file_copy).st_size, file_size)
        self.assertEqual(hash_code, build_dislosures_sha256(output_file_copy))
        return file_size, hash_code

    def test_write_3_files(self):
        input_file1 = "../files/4043_0.pdf"
        file_size1, hash1 = self.write_and_read(input_file1)

        self.assertEqual(0, self.server.convert_storage.check_storage())

        input_file2 = "../files/4043_1.pdf"
        self.write_and_read(input_file2)

        file_size_copy1, hash_copy1 = self.write_and_read(input_file1)
        self.assertEqual(file_size_copy1, file_size1)
        self.assertEqual(hash1, hash_copy1)
        # after this line TSnowBallFileStorage.bin_files[-1].tell() must be not at the file end

        input_file3 = "../files/4043_2.pdf"
        self.write_and_read(input_file3)

        stats = self.server.get_stats()
        self.assertEqual(stats["all_put_files_count"], 3)

        self.assertEqual(0, self.server.convert_storage.check_storage())


class TestHighLoadPing(TTestConvBase):

    def setUp(self):
        self.before_files = list()
        self.background_files = list()
        self.setup_server("many_pings2")

        for i in range(10):
            random_pdf_file = os.path.join( self.data_folder, "random_{}.pdf".format(i))
            self.converters.build_random_pdf(random_pdf_file, cnt=500)
            self.before_files.append(random_pdf_file)

        for i in range(5):
            random_pdf_file = os.path.join( self.data_folder, "random_background_{}.pdf".format(i))
            self.converters.build_random_pdf(random_pdf_file, cnt=500)
            self.background_files.append(random_pdf_file)

    def is_converting(self):
        return self.client.get_stats()['is_converting']

    def cpu_load(self):
        print("start cpu load at {}".format(time.time()))
        p = subprocess.Popen(["c:/cygwin64/bin/sha1sum", '/dev/zero'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        return p

    def send_a_file(self, file_path):
        log_name = os.path.basename(file_path) + "_log"
        self.process_with_client([file_path], timeout=2, skip_receiving=False, log_name=log_name)
        return True

    def check_alive(self):
        return self.client.assert_declarator_conv_alive(raise_exception=False)

    def test_many_pings(self):
        self.process_with_client(self.before_files, timeout=5, skip_receiving=False)

        #load two cpu cores with some tasks to be like production server
        pid_cpu_load1 = self.cpu_load()
        pid_cpu_load2 = self.cpu_load()

        time.sleep(5)
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            func_calls = list()
            for i in self.background_files:
                func_calls.append(partial(self.send_a_file, i))
            for i in range(40):
                if random.random() < 0.5:
                    f = self.check_alive
                else:
                    f = self.is_converting
                func_calls.append(f)
            random.shuffle(func_calls)
            requests = {executor.submit(f) for f in func_calls}
            for future in concurrent.futures.as_completed(requests):
                self.assertTrue(future.result())
        print("rps is {}".format(len(func_calls) / (time.time() - start)))
        pid_cpu_load1.kill()
        pid_cpu_load2.kill()

    def tearDown(self):
        subprocess.run(['taskkill', '/F', '/IM', 'sha1sum.exe'], stderr=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL)
        self.tear_down()


# use qpdf to strip drm
class TestQPDF(TTestConvBase):
    def setUp(self):
        self.setup_server("drm")

    def tearDown(self):
        self.tear_down()

    # the size of the output file must be less than 15000 (from Finereader), winword converts it to a chinese doc"
    def test_qpdf(self):
        output_files = self.process_with_client(["../files/drm.pdf"], timeout=240)
        self.assertTrue(os.path.exists(output_files[0]))
        file_size = os.stat(output_files[0]).st_size
        self.assertGreater(file_size, 12000)


# winword 2019 hangs on ../files/winword_hangs.pdf, we wait 30s(10m in prod) in test environment and pass this file to ocr.
# This test leaves a hanged winword instance, since server is started with --disable-killing-winword.
# I do not know how to make it simplier

class TestWinwordHangs(TTestConvBase):
    def setUp(self):
        self.setup_server("winword_hangs", ['--winword-timeout', '30s'])

    def tearDown(self):
        self.tear_down()

    def test_winword_hangs(self):
        file_path = "../files/winword2019_hangs.pdf"
        output_files = self.process_with_client([file_path], timeout=240, skip_receiving=True)
        sha256 = build_dislosures_sha256(file_path)
        for x in range(120):
            time.sleep(1)
            # server must answer and accept requests while winword is working(hanging) in background
            self.assertTrue(self.client.assert_declarator_conv_alive(raise_exception=False))
            if self.client.check_file_was_converted(sha256):
                self.client.retrieve_document(sha256, output_files[0])
                break

        self.assertTrue(os.path.exists(output_files[0]))
        file_size = os.stat(output_files[0]).st_size
        self.assertGreater(file_size, 5000)
        stats = self.server.get_stats()
        self.assertEqual(1, stats['finished_ocr_tasks'])


class TestExceptionInServiceActions(TTestConvBase):
    def setUp(self):
        self.setup_server("service_actions_exp", ['--central-heart-rate', '1', '--disable-winword',])

    def tearDown(self):
        self.tear_down()

    def test_exception_in_service_actions(self):
        # sometimes in service actions occurs an unknown exception, in this case we should exit from all threads
        # and exit from the program
        random_pdf_file = os.path.join(self.data_folder, "random.pdf")
        self.converters.build_random_pdf(random_pdf_file, cnt=500)
        self.process_with_client([random_pdf_file], skip_receiving=True, input_task_timeout=1)[0]
        time.sleep(5)
        self.client.stop_conversion_thread(timeout=2)
        self.server.ocr_tasks = None
        time.sleep(2)
        stats = self.server.get_stats()
        self.assertIsNotNone(stats.get('exception'))

