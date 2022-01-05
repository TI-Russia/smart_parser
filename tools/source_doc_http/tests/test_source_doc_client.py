import time

from source_doc_http.source_doc_server import TSourceDocHTTPServer
from source_doc_http.source_doc_client import TSourceDocClient
from common.primitives import build_dislosures_sha256


from unittest import TestCase
import os
import threading
import shutil


def start_server(server):
    server.serve_forever()
    print("start_server exit")


class TTestEnv:
    def __init__(self, port, max_bin_file_size=None, read_only=False, use_archives=False):
        self.port = port
        self.max_bin_file_size = max_bin_file_size
        self.data_folder = "data.{}".format(port)
        self.archive_folder = "archive.{}".format(port) if use_archives else None
        if self.archive_folder is not None:
            if os.path.exists(self.archive_folder):
                shutil.rmtree(self.archive_folder)
            os.mkdir(self.archive_folder)
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
            '--heart-rate', str(1),
        ]
        if self.max_bin_file_size is not None:
            server_args.extend(['--max-bin-file-size', str(self.max_bin_file_size)])
        if self.archive_folder is not None:
            server_args.extend(['--archive-folder', self.archive_folder])
            server_args.extend(['--header-archive-copy-timeout', str(1)])
        if read_only:
            server_args.extend(['--read-only'])
        self.server = TSourceDocHTTPServer(TSourceDocHTTPServer.parse_args(server_args))
        self.server_thread = threading.Thread(target=start_server, args=(self.server,))
        self.server_thread.start()

        client_args = [
            "--server-address", self.server_address,
        ]
        self.client = TSourceDocClient(TSourceDocClient.parse_args(client_args))

    def tearDown(self, stop_server=True):
        if stop_server:
            self.server.stop_server()
        self.server_thread.join(0)
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.chdir(os.path.dirname(__file__))


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
        sha256 = build_dislosures_sha256("test.txt")
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

        file_data_, _ = self.env.client.retrieve_file_data_by_sha256(build_dislosures_sha256("test1.txt"))
        self.assertEqual(file_data1, file_data_)

        file_data_, _ = self.env.client.retrieve_file_data_by_sha256(build_dislosures_sha256("test2.txt"))
        self.assertEqual(file_data2, file_data_)


class TestReload(TestCase):
    def setUp(self):
        self.env = TTestEnv(8494)

    def tearDown(self):
        self.env.tearDown()

    def test_reload(self):
        file_data1 = b"12345_1"
        file_path = "test8484.txt"
        with open(file_path, "wb") as outp:
            outp.write(file_data1)

        self.assertTrue(self.env.client.send_file("test8484.txt"))

        stats = self.env.client.get_stats()
        self.env.server.file_storage.close_file_storage()
        self.env.server.file_storage.load_from_disk()

        file_data_, _ = self.env.client.retrieve_file_data_by_sha256(build_dislosures_sha256(file_path))
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
        self.assertTrue( self.env.server.file_storage.check_storage(False) )

        file_data2 = b"12345_2"
        with open("test2.txt", "wb") as outp:
            outp.write(file_data2)

        self.assertTrue(self.env.client.send_file("test2.txt"))
        stats = self.env.client.get_stats()
        self.assertEqual(1, stats['source_doc_count'])


class TestExit(TestCase):
    port = 8495
    def setUp(self):
        self.env = TTestEnv(TestExit.port)

    def tearDown(self):
        self.env.tearDown(stop_server=False)

    def test_server_exit(self):
        file_data1 = b"12345_1"
        with open("test8484.txt", "wb") as outp:
            outp.write(file_data1)

        self.assertTrue(self.env.client.send_file("test8484.txt"))

        stats = self.env.client.get_stats(timeout=1)
        self.assertEqual(1, stats['source_doc_count'])
        with open(TSourceDocHTTPServer.stop_file, "w") as outp:
            outp.write(".")
        time.sleep(2)
        stats = self.env.client.get_stats(timeout=1)
        self.assertIsNone(stats)


class TestSourceDocArchive(TestCase):

    def setUp(self):
        self.env = TTestEnv(8496, 4, use_archives=True)

    def tearDown(self):
        self.env.tearDown()

    def test_many_bin_files_with_archive(self):
        file_data1 = b"12345_1"
        with open("test1.txt", "wb") as outp:
            outp.write(file_data1)
        file_data2 = b"12345_2"
        with open("test2.txt", "wb") as outp:
            outp.write(file_data2)

        self.assertTrue(self.env.client.send_file("test1.txt"))
        time.sleep(1)
        self.assertTrue(self.env.client.send_file("test2.txt"))
        stats = self.env.client.get_stats()
        self.assertEqual(stats['bin_files_count'], 2)
        archive_files = os.listdir(self.env.archive_folder)
        self.assertEqual(2, len(archive_files))
        self.assertIn('header.dbm', archive_files)

