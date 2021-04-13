from  source_doc_http.source_doc_client import TSourceDocClient
from DeclDocRecognizer.external_convertors import EXTERNAl_CONVERTORS
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
from common.logging_wrapper import setup_logging

import sys
import  os

if __name__ == "__main__":

    INPUT_SHA256 = sys.argv[1]
    log_file_name = INPUT_SHA256 + ".log"
    logger = setup_logging(log_file_name=log_file_name)
    assert len(INPUT_SHA256) == 64
    source_doc_client = TSourceDocClient(TSourceDocClient.parse_args(["--disable-first-ping"]), logger=logger)
    file_data, file_extension = source_doc_client.retrieve_file_data_by_sha256(INPUT_SHA256)
    if file_data is None:
        logger.error("cannot find source document {}".format(INPUT_SHA256))
        sys.exit(1)
    file_path = "{}{}".format(INPUT_SHA256, file_extension)
    with open(file_path, "wb") as outp:
        outp.write(file_data)

    sha256, json_data = EXTERNAl_CONVERTORS.run_smart_parser_official(file_path,
                                                                      logger=logger,
                                                                      default_value=TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT)
    args = TSmartParserCacheClient.parse_args([])
    sp_client = TSmartParserCacheClient(args, logger=logger)
    json_path = file_path + ".json"
    with open (json_path, "wb") as outp:
        outp.write(json_data)
    sp_client.send_file(json_path, external_json=True)
    os.unlink(json_path)
    os.unlink(log_file_name)

