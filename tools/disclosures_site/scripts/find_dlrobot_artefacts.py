import argparse
from common.logging_wrapper import setup_logging
from pathlib import Path
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-site", dest='web_site')
    parser.add_argument("--exact", dest='exact', action="store_true", default=False, help="exact match web domain")
    parser.add_argument("--only-last", dest='only_last', action="store_true", default=False)
    parser.add_argument('--archive-folder', dest='archive_folder', default='/home/sokirko/declarator_hdd/Yandex.Disk/declarator/dlrobot_updates')
    return parser.parse_args()


class TDlrobotArchive:
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(log_file_name="find_dlrobot_artefacts.log")
        self.archive_paths = None
        self.build_archive_paths()

    def build_archive_paths(self):
        self.archive_paths = list()
        for p in sorted(Path(self.args.archive_folder).iterdir(), key=os.path.getmtime, reverse=True):
            if p.is_dir():
                self.archive_paths.append(p)
        self.logger.info('process {} archives from {}'.format(len(self.archive_paths), self.args.archive_folder))

    def find_archives(self):
        substring = self.args.web_site
        if self.args.exact:
            substring = "/" + substring + "."

        for a in self.archive_paths:
            file_list = os.path.join(a, 'processed_projects_file_list.txt')
            artefacts = list()
            with open (file_list) as inp:
                for l in inp:
                    if l.find(substring) != -1:
                        artefacts.append(l.strip())
            if len(artefacts) > 0:
                yield os.path.join(a, 'processed_projects.tar.gz'), artefacts
                if self.args.only_last:
                    break

    def unarchive(self, archive, files):
        file_list_path = "tmp_file_list"
        with open(file_list_path, "w") as outp:
            for f in files:
                outp.write(f + "\n")
        cmd = "tar --verbose --extract --file {} --files-from={} ".format(archive, file_list_path)
        self.logger.info(cmd)
        os.system(cmd)

    def main(self):
        for archive, files in self.find_archives():
            self.unarchive(archive, files)


if __name__ == '__main__':
    TDlrobotArchive(parse_args()).main()