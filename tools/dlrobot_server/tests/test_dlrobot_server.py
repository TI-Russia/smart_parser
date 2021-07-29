from dlrobot_server.dlrobot_central import TDlrobotHTTPServer
from dlrobot_server.dlrobot_worker import TDlrobotWorker
from dlrobot_server.scripts.fns.unzip_archive import TUnzipper
from dlrobot_server.common_server_worker import TTimeouts, PITSTOP_FILE
from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
from source_doc_http.source_doc_server import TSourceDocHTTPServer
from web_site_db.web_site_status import TWebSiteReachStatus
from web_site_db.web_sites import TDeclarationRounds
from common.primitives import build_dislosures_sha256, is_local_http_port_free
from common.urllib_parse_pro import TUrlUtf8Encode
from common.archives import TDearchiver
from unittest import TestCase
from disclosures_site.scripts.join_human_and_dlrobot import TJoiner
from declarations.input_json import TSourceDocument, TDlrobotHumanFile

import os
import threading
import shutil
import time
import json
import http.server
from functools import partial
import datetime


def start_server(server):
    try:
        server.serve_forever()
    except Exception as exp:
        pass


def start_worker(client):
    client.run_thread_pool()


class TTestEnv:

    def __init__(self, central_port):
        assert is_local_http_port_free(central_port)
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

    def setup_website(self, port, html_folder="web_sites/simple"):
        assert is_local_http_port_free(port)
        directory = os.path.join(os.path.dirname(__file__), html_folder)
        assert os.path.exists(directory)
        handler = partial(http.server.SimpleHTTPRequestHandler, directory=directory)
        self.web_site = http.server.HTTPServer(server_address=("127.0.0.1", port), RequestHandlerClass=handler)
        threading.Thread(target=start_server, args=(self.web_site,)).start()

    def setup_smart_parser_server(self, port):
        assert is_local_http_port_free(port)
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
        round_file = os.path.join(self.data_folder, "dlrobot_rounds.json")
        with open(round_file, "w") as outp:
            yesterday = (datetime.date.today() - datetime.timedelta(days=1))
            json.dump(TDeclarationRounds.build_an_example(yesterday), outp)
        server_args = [
            '--input-task-list', self.input_web_sites_file,
            '--remote-calls-file', remote_calls_file_name,
            '--result-folder', self.result_folder,
            '--server-address', self.central_address,
            '--tries-count', str(tries_count),
            '--central-heart-rate', '1s',
            '--dlrobot-crawling-timeout', str(dlrobot_project_timeout),
            '--log-file-name', os.path.join(self.data_folder, "dlrobot_central.log"),
            '--disable-search-engines',
            '--disable-telegram',
            '--disable-pdf-conversion-server-checking',
            '--round-file', round_file
        ]
        if not enable_smart_parser:
            server_args.append('--disable-smart-parser-server')
        if not enable_source_doc_server:
            server_args.append('--disable-source-doc-server')
        self.central = TDlrobotHTTPServer(TDlrobotHTTPServer.parse_args(server_args))
        self.central_thread = threading.Thread(target=start_server, args=(self.central,))
        self.central_thread.start()

    def setup_worker(self, action, fake_dlrobot=False):
        os.mkdir(self.worker_folder)
        worker_args = [
            '--server-address', self.central_address,
            '--working-folder', self.worker_folder,
            '--timeout-before-next-task', '1'
        ]
        if fake_dlrobot:
            worker_args.append('--fake-dlrobot')
        worker_args.append(action)
        self.worker = TDlrobotWorker(TDlrobotWorker.parse_args(worker_args))
        self.start_worker_thread()

    def setup_source_doc_server(self, port):
        assert is_local_http_port_free(port)
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
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)

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

    def build_history_file(self, web_sites, file_name, set_end_time_to_none=False):
        start_time = int(time.time())
        with open(file_name, "w") as outp:
            for web_site, result_files in web_sites:
                rec = {"worker_ip": "95.165.96.61",
                       "project_file": web_site + ".txt",
                       "web_site": web_site,
                       "exit_code": 0,
                       "start_time": start_time,
                       "end_time": start_time + 1,
                       "result_folder": None,
                       "reach_status": TWebSiteReachStatus.normal,
                       "result_files_count": result_files,
                       "worker_host_name": None}
                if set_end_time_to_none:
                    rec["end_time"] = None
                json.dump(rec, outp)
                outp.write("\n")


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
        self.assertEqual(1, stats['running_count'])
        self.env.worker_thread.join(200)
        self.assertEqual(1, self.env.count_projects_results())
        self.assertTrue(TWebSiteReachStatus.can_communicate(self.env.get_last_reach_status()))
        # one more time
        self.env.start_worker_thread()
        self.env.worker_thread.join(200)


class TestBadDomain(TestCase):
    central_port = 8291

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_central(False, ".bad_domain")
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


class WorkerPitStop(TestCase):
    central_port = 8292

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_worker("start")

    def tearDown(self):
        self.env.tearDown()

    def test_worker_pitstop(self):
        with open(os.path.join(self.env.worker_folder, PITSTOP_FILE), "w"):
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
        with open (os.path.join(self.env.data_folder, PITSTOP_FILE), "w"):
            pass
        time.sleep(self.env.central.args.central_heart_rate + 1)
        self.assertTrue( self.env.central.stop_process )
        self.assertFalse(self.env.central_thread.is_alive())


class DlrobotTimeout(TestCase):
    central_port = 8294

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_central(False, ".bad_domain", dlrobot_project_timeout=2, tries_count=1)
        self.env.setup_worker("run_once")

    def tearDown(self):
        self.env.tearDown()

    def test_timeout(self):
        old_timeouts = TTimeouts.save_timeouts()
        TTimeouts.set_timeouts(0)
        self.assertTrue(self.env.worker_thread.is_alive())
        time.sleep(2)
        self.env.worker.stop_worker()
        time.sleep(2)
        TTimeouts.restore_timeouts(old_timeouts)
        stats = self.env.central.get_stats()

        # still have the project in the input tasks since timeouted project have one more retry
        # remember that yandex cloud workstations are restarted each day, all projects from them are timeouted
        self.assertEqual(stats['input_tasks'], 1)
        self.assertEqual(stats['processed_tasks'], 1)


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


class TestHistoryFiles(TestCase):
    central_port = 8305

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        history_file = os.path.join(self.env.data_folder, "history.txt")
        self.env.build_history_file([("olddomain.ru", 1),
                                     ("olddomain.ru", 1),
                                     ("olddomain2.ru", 0)], history_file)
        self.env.setup_central(False, ["olddomain.ru", "newdomain.ru", "olddomain2.ru"], history_file=history_file)

    def tearDown(self):
        self.env.tearDown()

    def test_task_order(self):
        # there is no newdomain.ru in the history, that's why it goes before olddomain2.ru
        self.assertListEqual(["newdomain.ru", "olddomain2.ru"], self.env.central.web_sites_to_process)


class TestHistoryFiles2(TestCase):
    central_port = 8308

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        history_file = os.path.join(self.env.data_folder, "history.txt")
        self.env.build_history_file([
                ("a.ru", 1),
                ("b.ru", 0)], history_file)
        self.env.setup_central(False, ["a.ru", "b.ru"], history_file=history_file)

    def tearDown(self):
        self.env.tearDown()

    def test_b_ru_was_a_success(self):
        self.assertListEqual(["b.ru"], self.env.central.web_sites_to_process)


class TestHistoryFiles3(TestCase):
    central_port = 8308

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        history_file = os.path.join(self.env.data_folder, "history.txt")
        self.env.build_history_file([
                ("a.ru", 0),
                ("a.ru", 0),
                ("b.ru", 0)], history_file)
        self.env.setup_central(False, ["a.ru", "b.ru"], history_file=history_file)

    def tearDown(self):
        self.env.tearDown()

    def test_website_a_ru_has_enough_tries(self):
        self.assertListEqual(["b.ru"], self.env.central.web_sites_to_process)


class TestHistoryFiles4(TestCase):
    central_port = 8309

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        history_file = os.path.join(self.env.data_folder, "history.txt")
        self.env.build_history_file([
                ("a.ru", 0),
                ("a.ru", 0),
                ], history_file, set_end_time_to_none=True)
        self.env.setup_central(False, ["a.ru"], history_file=history_file)

    def tearDown(self):
        self.env.tearDown()

    def test_one_more_retry_for_lost_tasks(self):
        self.assertListEqual(["a.ru"], self.env.central.web_sites_to_process)


class TestRussianDomain(TestCase):
    central_port = 8310

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_central(False, "лотошинье.рф")
        self.env.setup_worker("run_once", fake_dlrobot=True)

    def tearDown(self):
        self.env.tearDown()

    def test_Russsian_domain(self):
        self.env.worker_thread.join(200)
        self.assertEqual(1, self.env.count_projects_results())
        self.assertEqual(1, self.env.central.get_stats()['processed_tasks'])


class DlrobotIncomeYearInAnchorText(TestCase):
    central_port = 8310
    website_port = 8311
    smart_parser_server_port = 8312

    def setUp(self):
        self.env = TTestEnv(self.central_port)
        self.env.setup_website(self.website_port, html_folder="web_sites/declaration_year_in_anchor")
        self.env.setup_smart_parser_server(self.smart_parser_server_port)
        self.env.setup_central(True, "127.0.0.1:{}".format(self.website_port))
        self.env.setup_worker("run_once")

    def tearDown(self):
        self.env.tearDown()

    def test_year_in_anchor_text(self):
        self.env.worker_thread.join(200)
        self.assertEqual(self.env.count_projects_results(), 1)
        time.sleep(5)  # give time for smart parser to process documents
        self.assertEqual(self.env.smart_parser_server.get_stats()['session_write_count'], 1)
        dlrobot_human_json_path = os.path.join(self.env.data_folder, "dlrobot_human.json")
        human_json_path = os.path.join(self.env.data_folder, "human.json")
        TDlrobotHumanFile(human_json_path, read_db=False).write()

        args = ['--max-ctime', '5602811863', #the far future
                '--input-dlrobot-folder', self.env.result_folder,
                '--human-json', human_json_path,
                '--output-json', dlrobot_human_json_path
                ]
        joiner = TJoiner(TJoiner.parse_args(args))
        joiner.main()
        dlrobot_human = TDlrobotHumanFile(dlrobot_human_json_path)
        self.assertEqual(1,  dlrobot_human.get_documents_count())
        src_doc: TSourceDocument
        src_doc = list(dlrobot_human.document_collection.values())[0]
        self.assertEqual(2020, src_doc.get_external_income_year_from_dlrobot())


class WebSiteWithSubdirectory(TestCase):
    central_port = 8313
    website_port = 8314
    smart_parser_server_port = 8315

    def setUp(self):
        self.site_url = "127.0.0.1:{}/ru".format(self.website_port)
        self.env = TTestEnv(self.central_port)
        self.env.setup_website(self.website_port, html_folder="web_sites/site_with_subfolder")
        self.env.setup_smart_parser_server(self.smart_parser_server_port)
        self.env.setup_central(True, self.site_url)
        self.env.setup_worker("run_once")

    def tearDown(self):
        self.env.tearDown()

    def test_site_with_subdirectory(self):
        self.env.worker_thread.join(200)
        self.assertEqual(self.env.count_projects_results(), 1)
        time.sleep(5)  # give time for smart parser to process documents
        self.assertEqual(self.env.smart_parser_server.get_stats()['session_write_count'], 1)
        dlrobot_human_json_path = os.path.join(self.env.data_folder, "dlrobot_human.json")
        human_json_path = os.path.join(self.env.data_folder, "human.json")
        TDlrobotHumanFile(human_json_path, read_db=False).write()

        args = ['--max-ctime', '5602811863', #the far future
                '--input-dlrobot-folder', self.env.result_folder,
                '--human-json', human_json_path,
                '--output-json', dlrobot_human_json_path
                ]
        joiner = TJoiner(TJoiner.parse_args(args))
        joiner.main()
        dlrobot_human = TDlrobotHumanFile(dlrobot_human_json_path)
        self.assertEqual(1,  dlrobot_human.get_documents_count())
        src_doc: TSourceDocument
        src_doc = list(dlrobot_human.document_collection.values())[0]
        site_url = src_doc.get_web_site()
        self.assertEqual(self.site_url, site_url)
