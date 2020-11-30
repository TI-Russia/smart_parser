from unittest import TestCase
from source_doc_http.source_doc_server import TSourceDocHTTPServer
from source_doc_http.source_doc_client import TSourceDocClient
import os
import threading
import hashlib
import shutil


def start_server(server):
    server.serve_forever()


class TTestEnv:
    def __init__(self, port, max_bin_file_size=None):
        self.port = port
        self.max_bin_file_size = max_bin_file_size
        self.data_folder = "data.{}".format(port)
        self.server_address = "localhost:{}".format(self.port)
        self.server = None
        self.server_thread = None
        self.client = None
        self.setUp()

    def setUp(self):
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        class TArgs:
            data_folder = self.data_folder
            server_address = self.server_address
            log_file_name = "source_doc_server.{}.log".format(self.port)
            max_bin_file_size = self.max_bin_file_size

        self.server = TSourceDocHTTPServer(TArgs())
        self.server_thread = threading.Thread(target=start_server, args=(self.server,))
        self.server_thread.start()

        class TArgs:
            server_address = self.server_address
            timeout = 300
        self.client = TSourceDocClient(TArgs())

    def tearDown(self):
        self.server.close_files()
        self.server.server_close()
        self.server.shutdown()
        self.server_thread.join(0)
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)


class TestTSourceDocClient1(TestCase):
    def setUp(self):
        self.env = TTestEnv(8492)

    def tearDown(self):
        self.env.tearDown()

    def test_send_file_and_retrieve(self):
        file_data = b"12345"
        with open("test.txt", "wb") as outp:
            outp.write(file_data)
        self.assertTrue(self.env.client.send_file("test.txt"))
        stats = self.env.client.get_stats()
        self.assertEqual(stats['source_doc_count'], 1)
        sha256 = hashlib.sha256(file_data).hexdigest()
        file_data1, file_extension = self.env.client.retrieve_file_data_by_sha256(sha256)
        self.assertEqual(file_data1, file_data)
        self.assertEqual(file_extension, ".txt")


class TestTSourceDocClient2(TestCase):

    def setUp(self):
        self.env = TTestEnv(8493, 4)

    def tearDown(self):
        self.env.tearDown()

    def test_many_bin_files(self):
        file_data1 = b"12345_1"
        with open("test1.txt", "wb") as outp:
            outp.write(file_data1)
        file_data2 = b"12345_2"
        with open("test2.txt", "wb") as outp:
            outp.write(file_data2)

        self.assertTrue(self.env.client.send_file("test1.txt"))
        self.assertTrue(self.env.client.send_file("test2.txt"))
        stats = self.env.client.get_stats()
        self.assertEqual(stats['bin_files_count'], 2)

        file_data_, _ = self.env.client.retrieve_file_data_by_sha256(hashlib.sha256(file_data1).hexdigest())
        self.assertEqual(file_data1, file_data_)

        file_data_, _ = self.env.client.retrieve_file_data_by_sha256(hashlib.sha256(file_data2).hexdigest())
        self.assertEqual(file_data2, file_data_)


class TestReload(TestCase):
    def setUp(self):
        self.env = TTestEnv(8494)

    def tearDown(self):
        self.env.tearDown()

    def test_reload(self):
        file_data1 = b"12345_1"
        with open("test8484.txt", "wb") as outp:
            outp.write(file_data1)

        self.assertTrue(self.env.client.send_file("test1.txt"))

        stats = self.env.client.get_stats()
        self.env.server.close_files()
        self.env.server.load_from_disk()

        file_data_, _ = self.env.client.retrieve_file_data_by_sha256(hashlib.sha256(file_data1).hexdigest())
        self.assertEqual(file_data1, file_data_)

