from source_doc_http.source_doc_server import TSourceDocHTTPServer
from source_doc_http.source_doc_client import TSourceDocClient

from unittest import TestCase
import os
import threading
import hashlib
import shutil


def start_server(server):
    server.serve_forever()


class TTestEnv:
    def __init__(self, port, max_bin_file_size=None, read_only=False):
        self.port = port
        self.max_bin_file_size = max_bin_file_size
        self.data_folder = "data.{}".format(port)
        self.server_address = "localhost:{}".format(self.port)
        self.server = None
        self.server_thread = None
        self.client = None
        self.setUp(read_only)

    def setUp(self, read_only):
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        server_args = [
            "--server-address", self.server_address,
            '--log-file-name', "source_doc_server.{}.log".format(self.port),
            '--data-folder', self.data_folder,
        ]
        if self.max_bin_file_size is not None:
            server_args.extend(['--max-bin-file-size', str(self.max_bin_file_size)])
        if read_only:
            server_args.extend(['--read-only'])
        self.server = TSourceDocHTTPServer(TSourceDocHTTPServer.parse_args(server_args))
        self.server_thread = threading.Thread(target=start_server, args=(self.server,))
        self.server_thread.start()

        client_args = [
            "--server-address", self.server_address,
        ]
        self.client = TSourceDocClient(TSourceDocClient.parse_args(client_args))

    def tearDown(self):
        self.server.stop_server()
        self.server_thread.join(0)
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.chdir( os.path.dirname(__file__))


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

        self.assertTrue(self.env.client.send_file("test8484.txt"))

        stats = self.env.client.get_stats()
        self.env.server.file_storage.close_file_storage()
        self.env.server.file_storage.load_from_disk()

        file_data_, _ = self.env.client.retrieve_file_data_by_sha256(hashlib.sha256(file_data1).hexdigest())
        self.assertEqual(file_data1, file_data_)


class TestReadOnly(TestCase):
    def setUp(self):
        self.env = TTestEnv(8495)

    def tearDown(self):
        self.env.tearDown()

    def test_read_only(self):
        file_data1 = b"12345_1"
        with open("test8484.txt", "wb") as outp:
            outp.write(file_data1)

        self.assertTrue(self.env.client.send_file("test8484.txt"))

        stats = self.env.client.get_stats()
        self.assertEqual(1, stats['source_doc_count'])


        self.env.server.file_storage.close_file_storage()
        self.env.server.file_storage.read_only = True
        self.env.server.file_storage.load_from_disk()

        file_data2 = b"12345_2"
        with open("test2.txt", "wb") as outp:
            outp.write(file_data2)

        self.assertTrue(self.env.client.send_file("test2.txt"))
        stats = self.env.client.get_stats()
        self.assertEqual(1, stats['source_doc_count'])
