from dlrobot_server.dlrobot_central import TDlrobotHTTPServer
from dlrobot_server.dlrobot_worker import TDlrobotWorker
from dlrobot_server.scripts.fns.unzip_archive import TUnzipper
from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
from source_doc_http.source_doc_server import TSourceDocHTTPServer
from web_site_db.robot_web_site import TWebSiteReachStatus
from common.primitives import build_dislosures_sha256
from common.archives import TDearchiver
from unittest import TestCase
import os
import threading
import shutil
import time
import json
import http.server
from functools import partial


def start_server(server):
    try:
        server.serve_forever()
    except Exception as exp:
        pass


def start_worker(client):
    client.run_thread_pool()


def is_port_free(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


class TTestEnv:

    def __init__(self, central_port):
        assert is_port_free(central_port)
        self.central_port = central_port
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.{}".format(central_port))
        self.central_address = "127.0.0.1:{}".format(self.central_port)
        self.central = None
        self.central_thread = None
        self.worker_thread = None
        self.worker = None
        self.input_web_sites_file = None
        self.result_folder = None
        self.worker_folder = os.path.join(self.data_folder, "workdir")
        self.web_site = None
        self.source_doc_server = None
        self.smart_parser_server = None
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)

    def setup_website(self, port):
        assert is_port_free(port)
        handler = partial(http.server.SimpleHTTPRequestHandler,
                          directory=os.path.join(os.path.dirname(__file__), "html"))
        self.web_site = http.server.HTTPServer(server_address=("127.0.0.1", port), RequestHandlerClass=handler)
        threading.Thread(target=start_server, args=(self.web_site,)).start()

    def setup_smart_parser_server(self, port):
        assert is_port_free(port)
        input_folder = os.path.join(self.data_folder, "smart_parser_serve_input")
        server_args = ['--input-task-directory', input_folder]
        os.environ['SMART_PARSER_SERVER_ADDRESS'] = '127.0.0.1:{}'.format(port)
        self.smart_parser_server = TSmartParserHTTPServer(TSmartParserHTTPServer.parse_args(server_args))
        threading.Thread(target=start_server, args=(self.smart_parser_server,)).start()

    def build_web_sites_file(self, web_site):
        self.input_web_sites_file = os.path.join(self.data_folder, "web_sites.json")
        with open(self.input_web_sites_file, "w") as outp:
            if web_site is not None:
                if not isinstance(web_site, list):
                    web_sites = [web_site]
                else:
                    web_sites = web_site
                js = dict()
                for w in web_sites:
                    js[w] = {
                        "calc_office_id": None
                    }
            else:
                js = {}
            json.dump(js, outp, indent=4, ensure_ascii=False)

    def setup_central(self, enable_smart_parser, web_site, dlrobot_project_timeout=5*60, tries_count=2,
                      enable_source_doc_server=False, history_file=None):
        self.build_web_sites_file(web_site)
        self.result_folder = os.path.join(self.data_folder, "processed_projects")
        if history_file is None:
            remote_calls_file_name = os.path.join(self.data_folder, "dlrobot_remote_calls.dat")
            with open(remote_calls_file_name, "w"):
                pass
        else:
            remote_calls_file_name = history_file
        server_args = [
            '--input-task-list', self.input_web_sites_file,
            '--remote-calls-file', remote_calls_file_name,
            '--result-folder', self.result_folder,
            '--server-address', self.central_address,
            '--tries-count', str(tries_count),
            '--central-heart-rate', '1s',
            '--dlrobot-project-timeout', str(dlrobot_project_timeout),
            '--log-file-name', os.path.join(self.data_folder, "dlrobot_central.log"),
            '--disable-search-engines',
            '--disable-telegram',
            '--disable-pdf-conversion-server-checking'
        ]
        if not enable_smart_parser:
            server_args.append('--disable-smart-parser-server')
        if not enable_source_doc_server:
            server_args.append('--disable-source-doc-server')
        self.central = TDlrobotHTTPServer(TDlrobotHTTPServer.parse_args(server_args))
        self.central_thread = threading.Thread(target=start_server, args=(self.central,))
        self.central_thread.start()

    def setup_worker(self, action):
        os.mkdir(self.worker_folder)
        worker_args = [
            '--server-address', self.central_address,
            '--working-folder', self.worker_folder,
            '--timeout-before-next-task', '1',
            action
        ]
        self.worker = TDlrobotWorker(TDlrobotWorker.parse_args(worker_args))
        self.start_worker_thread()

    def setup_source_doc_server(self, port):
        assert is_port_free(port)
        sourec_doc_data_folder = os.path.join(self.data_folder, "source_doc_data")
        os.mkdir(sourec_doc_data_folder)
        server_args = [
            '--log-file-name', os.path.join(self.data_folder, "source_doc_server.log"),
            '--data-folder', sourec_doc_data_folder
            ]
        os.environ['SOURCE_DOC_SERVER_ADDRESS'] = '127.0.0.1:{}'.format(port)
        self.source_doc_server = TSourceDocHTTPServer(TSourceDocHTTPServer.parse_args(server_args))
        threading.Thread(target=start_server, args=(self.source_doc_server,)).start()

    def start_worker_thread(self):
        self.worker_thread = threading.Thread(target=start_worker, args=(self.worker,))
        self.worker_thread.start()

    def tearDown(self):
        if self.worker is not None:
            self.worker.stop_worker()
        if self.central:
            self.central.stop_server()
            self.central_thread.join(0)
        if self.worker is not None:
            self.worker_thread.join(0)
        if self.web_site is not None:
            print ('web_site shutdown')
            self.web_site.shutdown()
        if self.smart_parser_server is not None:
            self.smart_parser_server.stop_server()
        if self.source_doc_server is not None:
            self.source_doc_server.stop_server()
        #if os.path.exists(self.data_folder):
        #    shutil.rmtree(self.data_folder, ignore_errors=True)

    def count_projects_results(self):
        result_summary_count = 0
        for root, dirs, files in os.walk(self.result_folder):
            for filename in files:
                if filename.endswith('.visited_pages'):
                    result_summary_count += 1
        return result_summary_count

    def get_last_reach_status(self):
        remote_calls = list(self.central.dlrobot_remote_calls.get_all_calls())
        assert len(remote_calls) > 0
        return remote_calls[-1].reach_status


class TestAotRu(TestCase):
    central_port = 8290

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_central(False, "www.aot.ru")
        self.env.setup_worker("run_once")

    def tearDown(self):
        self.env.tearDown()

    def test_aot_ru(self):
        time.sleep(2)
        stats = self.env.central.get_stats()
        self.assertEqual(stats['running_count'], 1)
        self.env.worker_thread.join(200)
        self.assertEqual(1, self.env.count_projects_results())
        self.assertEqual(self.env.get_last_reach_status(), TWebSiteReachStatus.normal)
        # one more time
        self.env.start_worker_thread()
        self.env.worker_thread.join(200)


class TestBadDomain(TestCase):
    central_port = 8291

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_central(False, "bad_domain")
        self.env.setup_worker("run_once")

    def tearDown(self):
        self.env.tearDown()

    def test_bad_domain_and_two_retries(self):
        self.env.worker_thread.join(200)
        self.assertEqual(1, self.env.count_projects_results())
        self.assertEqual(1, self.env.central.get_stats()['processed_tasks'])
        self.assertEqual(self.env.get_last_reach_status(), TWebSiteReachStatus.abandoned)

        self.env.start_worker_thread()
        self.env.worker_thread.join(200)
        self.assertEqual(2, self.env.central.get_stats()['processed_tasks'])

        self.env.start_worker_thread()
        self.env.worker_thread.join(200)
        self.assertEqual(2, self.env.central.get_stats()['processed_tasks'])
        self.assertEqual(TWebSiteReachStatus.out_of_reach2,
        self.env.central.web_sites_db.get_web_site("bad_domain").reach_status)


class WorkerPitStop(TestCase):
    central_port = 8292

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_worker("start")

    def tearDown(self):
        self.env.tearDown()

    def test_worker_pitstop(self):
        with open (os.path.join(self.env.worker_folder, ".dlrobot_pit_stop"), "w"):
            pass
        time.sleep(3)
        self.assertFalse(self.env.worker_thread.is_alive())


class CentralPitStop(TestCase):
    central_port = 8293

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_central(False, None)

    def tearDown(self):
        self.env.tearDown()

    def test_central_pitstop(self):
        self.assertTrue(self.env.central_thread.is_alive())
        with open (os.path.join(self.env.data_folder, ".dlrobot_pit_stop"), "w"):
            pass
        time.sleep(3)
        self.assertFalse(self.env.central_thread.is_alive())


class DlrobotTimeout(TestCase):
    central_port = 8294

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_central(False, "bad_domain", dlrobot_project_timeout=2, tries_count=1)
        self.env.setup_worker("run_once")

    def tearDown(self):
        self.env.tearDown()

    def test_timeout(self):
        self.assertTrue(self.env.worker_thread.is_alive())
        time.sleep(2)
        self.env.worker.stop_worker()
        time.sleep(2)
        stats = self.env.central.get_stats()

        # still have the project in the input tasks since timeouted project have one more retry
        # remember that yandex cloud workstations are restarted each day, all projects from them are timeouted
        self.assertEqual(stats['input_tasks'], 1)
        self.assertEqual(stats['processed_tasks'], 1)


# class DlrobotWebStats(TestCase):
#     central_port = 8295
#     website_port = 8296
#
#     def setUp(self):
#         self.env = TTestEnv(self.central_port)
#         self.env.setup_website(self.website_port)
#         self.env.setup_central(False, "127.0.0.1:{}".format(self.website_port))
#         self.env.setup_worker("run_once")
#
#     def tearDown(self):
#         self.env.tearDown()
#
#     def test_web_stats(self):
#         self.env.worker_thread.join(200)
#         self.assertEqual(self.env.count_projects_results(), 1)
#         stat_file = os.path.join(self.env.result_folder, "dlrobot_remote_calls.dat")
#         stats = TDlrobotAllStats(TDlrobotAllStats.parse_args(['--central-stats-file', stat_file]))
#         stats.build_stats() # check no exceptions


class DlrobotWithSmartParser(TestCase):
    central_port = 8297
    website_port = 8298
    smart_parser_server_port = 8299

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_website(self.website_port)
        self.env.setup_smart_parser_server(self.smart_parser_server_port)
        self.env.setup_central(True, "127.0.0.1:{}".format(self.website_port))
        self.env.setup_worker("run_once")

    def tearDown(self):
        self.env.tearDown()

    def test_with_smart_parser(self):
        self.env.worker_thread.join(200)
        self.assertEqual(self.env.count_projects_results(), 1)
        time.sleep(5) # give time for smart parser to process documents
        self.assertEqual(self.env.smart_parser_server.get_stats()['session_write_count'], 1)


class DlrobotWithSmartParserAndSourceDocServer(TestCase):
    central_port = 8300
    website_port = 8301
    smart_parser_server_port = 8302
    source_doc_server_port = 8304

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_website(self.website_port)
        self.env.setup_smart_parser_server(self.smart_parser_server_port)
        self.env.setup_source_doc_server(self.source_doc_server_port)

        self.env.setup_central(True, "127.0.0.1:{}".format(self.website_port), enable_source_doc_server=True)
        self.env.setup_worker("run_once")

    def tearDown(self):
        self.env.tearDown()

    def test_dlrobot_with_smart_parser_and_source_doc_server(self):
        self.env.worker_thread.join(200)
        self.assertEqual(self.env.count_projects_results(), 1)
        time.sleep(5) # give time for smart parser to process documents
        self.assertEqual(self.env.smart_parser_server.get_stats()['session_write_count'], 1)

        stats = self.env.source_doc_server.get_stats()
        self.assertEqual(stats['source_doc_count'], 1)


class TestHistoryFiles(TestCase):
    central_port = 8305

    def build_history_file(self, web_sites, file_name):
        with open(file_name, "w") as outp:
            for web_site in web_sites:
                rec = {"worker_ip": "95.165.96.61",
                       "project_file": web_site + ".txt",
                       "web_site": web_site,
                       "exit_code": 0,
                       "start_time": 1601799469,
                       "end_time": None,
                       "result_folder": None,
                       "reach_status": TWebSiteReachStatus.normal,
                       "result_files_count": 0, "worker_host_name": None}
                json.dump(rec, outp)
                outp.write("\n")

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        history_file = os.path.join(self.env.data_folder, "history.txt")
        self.build_history_file(["olddomain.ru", "olddomain.ru", "olddomain2.ru"], history_file)
        self.env.setup_central(False, ["olddomain.ru", "newdomain.ru", "olddomain2.ru"], history_file=history_file)

    def tearDown(self):
        self.env.tearDown()

    def test_task_order(self):
        self.assertListEqual(["newdomain.ru", "olddomain2.ru", "olddomain.ru"],
                                self.env.central.web_sites_to_process)


class TestUnzipArchive(TestCase):
    central_port = 8306
    website_port = 8307
    smart_parser_server_port = 8308
    source_doc_server_port = 8309

    def setUp(self):
        self.input_archive_path = os.path.join(os.path.dirname(__file__), 'page.zip')
        self.env = TTestEnv(self.central_port)
        self.env.setup_website(self.website_port)
        self.env.setup_smart_parser_server(self.smart_parser_server_port)
        self.env.setup_source_doc_server(self.source_doc_server_port)

        self.env.setup_central(True, "127.0.0.1:{}".format(self.website_port), enable_source_doc_server=True)

        os.mkdir(self.env.worker_folder)
        worker_args = [
            '--server-address', self.env.central_address,
            '--archive', self.input_archive_path,
            '--web-domain', 'service.nalog.ru'
        ]
        self.unzipper = TUnzipper(TUnzipper.parse_args(worker_args))

    def tearDown(self):
        self.env.tearDown()

    def test_unzip(self):
        self.unzipper.dearchive_and_send()

        time.sleep(5)
        self.assertEqual(1, self.env.count_projects_results())

        time.sleep(5)
        self.assertEqual(1, self.env.smart_parser_server.get_stats()['session_write_count'])

        stats = self.env.source_doc_server.get_stats()
        self.assertEqual(1, stats['source_doc_count'])
        for _, _, file_path in TDearchiver(self.env.smart_parser_server.logger, "/tmp").unzip_one_archive(self.input_archive_path, "1"):
            sha256 = build_dislosures_sha256(file_path)
            os.remove(file_path)
            break
        js = json.loads(self.env.smart_parser_server.get_smart_parser_json(sha256))
        self.assertEqual('51.service.nalog.ru', js['document_sheet_props'][0]['url'])
