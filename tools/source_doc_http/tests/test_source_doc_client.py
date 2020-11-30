from unittest import TestCase
from source_doc_http.source_doc_server import TSourceDocHTTPServer, TSourceDocRequestHandler
from source_doc_http.source_doc_client import TSourceDocClient
import os
import threading
import hashlib
import shutil

def start_server(server):
    server.serve_forever()


class TestTSourceDocClient(TestCase):

    def setUp(self):
        if os.path.exists('data'):
            shutil.rmtree('data', ignore_errors=True)
        os.mkdir("data")
        os.environ['SOURCE_DOC_SERVER_ADDRESS'] = "localhost:8491"
        class TArgs:
            data_folder = "data"
            server_address = os.environ['SOURCE_DOC_SERVER_ADDRESS']
            log_file_name = "source_doc_server.log"
        TSourceDocRequestHandler.HTTP_SERVER = TSourceDocHTTPServer(TArgs())
        server_thread = threading.Thread(target=start_server, args=(TSourceDocRequestHandler.HTTP_SERVER,))
        server_thread.start()

    def test_send_file_and_retrieve(self):
        client = TSourceDocClient()
        file_data = b"12345"
        with open("test.txt", "wb") as outp:
            outp.write(file_data)
        self.assertTrue(client.send_file("test.txt"))
        stats = client.get_stats()
        self.assertEqual(stats['source_doc_count'], 1)
        sha256 = hashlib.sha256(file_data).hexdigest()
        file_data1, file_extension = client.retrieve_file_data_by_sha256(sha256)
        self.assertEqual(file_data1, file_data)
        self.assertEqual(file_extension, ".txt")

    def test_many_bin_files(self):
        TSourceDocHTTPServer.max_bin_file_size = 4
        file_data1 = b"12345_1"
        with open("test1.txt", "wb") as outp:
            outp.write(file_data1)
        file_data2 = b"12345_2"
        with open("test2.txt", "wb") as outp:
            outp.write(file_data2)

        client = TSourceDocClient()
        self.assertTrue(client.send_file("test1.txt"))
        self.assertTrue(client.send_file("test2.txt"))
        stats = client.get_stats()
        self.assertEqual(stats['bin_files_count'], 2)

        file_data_, _ = client.retrieve_file_data_by_sha256(hashlib.sha256(file_data1).hexdigest())
        self.assertEqual(file_data1, file_data_)

        file_data_, _ = client.retrieve_file_data_by_sha256(hashlib.sha256(file_data2).hexdigest())
        self.assertEqual(file_data2, file_data_)
