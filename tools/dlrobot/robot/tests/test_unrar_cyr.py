from common.archives import TDearchiver
from common.logging_wrapper import close_logger, setup_logging
from common.selenium_driver import TSeleniumDriver

from unittest import TestCase
import os
import shutil


class TestUnrar(TestCase):

    def test_unrar_cyr(self):
        logger = setup_logging(log_file_name="unrar.log")

        data_folder = os.path.join( os.path.dirname(__file__), "data_unrar")
        rar_path = os.path.join(os.path.dirname(__file__), "web_sites/unrar/file.rar")
        shutil.rmtree(data_folder, ignore_errors=True)
        os.makedirs(data_folder, exist_ok=True)
        driver = TSeleniumDriver(logger)  # it modifies os.environ
        driver.start_executable()
        # unrar cannot work with other locales ?
        #self.assertTrue(os.environ.get('LANG', "en").startswith('en'))
        d = TDearchiver(logger, data_folder)
        files = list(d.dearchive_one_archive(".rar", rar_path, 0))
        driver.stop_executable()
        self.assertEqual(len(files), 8)
        close_logger(logger)
        shutil.rmtree(data_folder, ignore_errors=True)