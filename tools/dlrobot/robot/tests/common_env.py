import os
import shutil


class TestDlrobotEnv:

    def __init__(self, data_folder=None):
        if data_folder is None:
            self.data_folder = data_folder
        else:
            self.data_folder = os.path.join(os.path.dirname(__file__), data_folder)
            if os.path.exists(self.data_folder):
                shutil.rmtree(self.data_folder, ignore_errors=True)
            os.mkdir(self.data_folder)
            os.chdir(self.data_folder)

    def delete_temp_folder(self):
        os.chdir(os.path.dirname(__file__))
        if os.environ.get("DEBUG_TESTS") is None:
            if self.data_folder is not None:
                shutil.rmtree(self.data_folder, ignore_errors=True)
