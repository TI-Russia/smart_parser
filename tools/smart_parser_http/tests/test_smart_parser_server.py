from unittest import TestCase
from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
import os
import threading
import shutil
import time


def start_server(server):
    server.serve_forever()


class TTestEnv:
    def __init__(self, port):
        self.port = port
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.{}".format(port))
        self.server_address = "localhost:{}".format(self.port)
        self.server = None
        self.server_thread = None
        self.client = None

    def setUp(self, worker_count, disk_sync_rate=1, heart_rate=600):
        TSmartParserHTTPServer.TASK_TIMEOUT = 1
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        server_args = [
            '--cache-file', os.path.join(self.data_folder, "smart_parser.dbm"),
            '--input-task-directory', os.path.join(self.data_folder, "input"),
            '--server-address', self.server_address,
            '--log-file-name', os.path.join(self.data_folder, "smart_parser_server.log"),
            '--worker-count', str(worker_count),
            '--disk-sync-rate', str(disk_sync_rate),
            '--heart-rate', str(heart_rate)
        ]
        self.server = TSmartParserHTTPServer(TSmartParserHTTPServer.parse_args(server_args))
        self.server_thread = threading.Thread(target=start_server, args=(self.server,))
        self.server_thread.start()

        class TArgs:
            server_address = self.server_address
            timeout = 300

        self.client = TSmartParserCacheClient(TArgs())

    def tearDown(self):
        self.server.stop_server()
        self.server_thread.join(0)
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)


class TestBasic(TestCase):
    def setUp(self):
        self.env = TTestEnv(8390)
        self.env.setUp(1)

    def tearDown(self):
        self.env.tearDown()

    def test_basic(self):
        file_path = os.path.join( os.path.dirname(__file__), "files/MainWorkPositionIncome.docx")
        self.assertEqual( self.env.client.retrieve_json_by_source_file(file_path), None)
        self.assertTrue(self.env.client.send_file(file_path))
        time.sleep(6)
        js = self.env.client.retrieve_json_by_source_file(file_path)

        self.assertIsNotNone(js)
        self.assertGreater(len(js), 0)
        stats = self.env.client.get_stats()
        self.assertEqual(stats["session_write_count"], 1)


class TestMultiThreaded(TestCase):
    def setUp(self):
        self.env = TTestEnv(8391)
        self.env.setUp(2)

    def tearDown(self):
        self.env.tearDown()

    def test_multi_threaded(self):
        file_path1 = os.path.join(os.path.dirname(__file__), "files/MainWorkPositionIncome.docx")
        self.assertTrue(self.env.client.send_file(file_path1))
        file_path2 = os.path.join(os.path.dirname(__file__), "files/RealtyNaturalText.docx")
        self.assertTrue(self.env.client.send_file(file_path2))

        time.sleep(6)

        js1 = self.env.client.retrieve_json_by_source_file(file_path1)
        self.assertIsNotNone(js1)
        self.assertGreater(len(js1), 0)

        js2 = self.env.client.retrieve_json_by_source_file(file_path2)
        self.assertIsNotNone(js2)
        self.assertGreater(len(js2), 0)

        stats = self.env.client.get_stats()
        self.assertEqual(stats["session_write_count"], 2)


class TestSyncByTimeout(TestCase):
    def setUp(self):
        self.env = TTestEnv(8392)
        self.env.setUp(2, disk_sync_rate=5, heart_rate=1)

    def tearDown(self):
        self.env.tearDown()

    def test_sync_by_timeout(self):
        file_path1 = os.path.join(os.path.dirname(__file__), "files/MainWorkPositionIncome.docx")
        self.assertTrue(self.env.client.send_file(file_path1))
        file_path2 = os.path.join(os.path.dirname(__file__), "files/RealtyNaturalText.docx")
        self.assertTrue(self.env.client.send_file(file_path2))

        time.sleep(8)
        stats = self.env.client.get_stats()
        self.assertEqual(stats['unsynced_records_count'], 0)

class TestRebuild(TestCase):
    def setUp(self):
        self.env = TTestEnv(8392)
        self.env.setUp(1)

    def tearDown(self):
        self.env.tearDown()

    def test_sync_by_timeout(self):
        file_path1 = os.path.join(os.path.dirname(__file__), "files/MainWorkPositionIncome.docx")
        self.assertTrue(self.env.client.send_file(file_path1))
        time.sleep(6)
        self.assertEqual(self.env.client.get_stats()['session_write_count'], 1)

        self.assertTrue(self.env.client.send_file(file_path1))
        time.sleep(6)
        self.assertEqual(self.env.client.get_stats()['session_write_count'], 1)

        self.assertTrue(self.env.client.send_file(file_path1, rebuild=True))
        time.sleep(6)
        self.assertEqual(self.env.client.get_stats()['session_write_count'], 2)
