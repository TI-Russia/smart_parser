import http.server
import sys
import threading
from robots.common.download import get_file_extension_only_by_headers, TDownloadedFile, \
             DEFAULT_HTML_EXTENSION, TDownloadEnv

HTTP_HEAD_REQUESTS_COUNT = 0
HTTP_GET_REQUESTS_COUNT = 0


class THttpServer(http.server.BaseHTTPRequestHandler):

    def build_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("Content-Disposition", 'attachment;filename = "wrong_name.doc"')
        self.end_headers()

    def do_GET(self):
        global HTTP_GET_REQUESTS_COUNT
        HTTP_GET_REQUESTS_COUNT += 1
        self.build_headers()
        self.wfile.write("<html> aaaaaaa </html>".encode("latin"))



    def do_HEAD(self):
        global HTTP_HEAD_REQUESTS_COUNT
        HTTP_HEAD_REQUESTS_COUNT += 1
        self.build_headers()


HTTP_SERVER = None
def start_server(host, port):
    global HTTP_SERVER
    HTTP_SERVER = http.server.HTTPServer((host, int(port)), THttpServer)
    HTTP_SERVER.serve_forever()


if __name__ == '__main__':
    TDownloadEnv.clear_cache_folder()
    web_addr = sys.argv[1]
    host, port = web_addr.split(":")
    server_thread = threading.Thread(target=start_server, args=(host, port))
    server_thread.start()
    url = web_addr +"/somepath"
    wrong_extension = get_file_extension_only_by_headers(url)
    assert wrong_extension == ".doc"   # see minvr.ru for this error
    downloaded_file = TDownloadedFile(url)
    right_extension = downloaded_file.file_extension  #read file contents to determine it's type
    assert right_extension == DEFAULT_HTML_EXTENSION
    HTTP_SERVER.shutdown()
    assert HTTP_GET_REQUESTS_COUNT == 1
    assert HTTP_HEAD_REQUESTS_COUNT == 1
