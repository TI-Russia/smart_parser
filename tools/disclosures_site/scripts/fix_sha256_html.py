# adhoc script for converting bad html sha256 codes (delete me in 2022!)

from common.primitives import build_dislosures_sha256_by_file_data
from common.file_storage import TFileStorage
from common.logging_wrapper import setup_logging
import sys
import dbm.gnu

if __name__ == "__main__":
    logger = setup_logging("fix_sha256_html")
    logger.debug ("open {} as source doc header".format(sys.argv[1]))
    source_doc_db = TFileStorage(logger, sys.argv[1], disc_sync_rate=10000)

    logger.debug("open {} as smart parser dbm".format(sys.argv[2]))
    smart_parser_dbm = dbm.gnu.open(sys.argv[2], "w")

    key = source_doc_db.saved_file_params.firstkey()
    html_extension = '.html'
    #html_extension = '.docx'
    html_keys = list()
    while key is not None:
        value = source_doc_db.saved_file_params[key].decode('utf8')
        if value.find(';{};'.format(html_extension)) != -1:
            html_keys.append(key)
        key = source_doc_db.saved_file_params.nextkey(key)

    logger.info("found {} html keys".format(len(html_keys)))

    for key in html_keys:
        value = source_doc_db.saved_file_params[key].decode('utf8')
        html_data, file_extension = source_doc_db.get_saved_file(key)
        assert html_extension == file_extension
        new_sha256 = build_dislosures_sha256_by_file_data(html_data, html_extension)
        logger.debug("{} -> {}".format(key, new_sha256))
        source_doc_db.saved_file_params[new_sha256] = source_doc_db.saved_file_params[key]
        del source_doc_db.saved_file_params[key]

        key_utf8 = key.decode('utf8')
        old_smart_parser_key = "{},{}".format(key_utf8, 0.1)
        new_smart_parser_key = "{},{}".format(new_sha256, 0.1)
        if old_smart_parser_key in smart_parser_dbm:
            logger.debug("{} -> {}".format(old_smart_parser_key, new_smart_parser_key))
            smart_parser_dbm[new_smart_parser_key] = smart_parser_dbm[old_smart_parser_key]
            del smart_parser_dbm[old_smart_parser_key]
        else:
            logger.error("{} does not exist in smart parser server".format(old_smart_parser_key))

    source_doc_db.close_file_storage()
    smart_parser_dbm.close()




