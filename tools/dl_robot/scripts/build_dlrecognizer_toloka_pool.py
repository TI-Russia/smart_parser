import argparse
import sys
import os
from common.robot_project import TRobotProject
from common.download import TDownloadedFile
from dl_robot.dlrobot import ROBOT_STEPS
from common.primitives import strip_html_url
from DeclDocRecognizer.external_convertors import TExternalConverters
import shutil
import csv
import time
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", dest='project', required=True)
    parser.add_argument("--output-toloka", dest='output_toloka')
    parser.add_argument("--input-assignments", dest='input_assignments')
    parser.add_argument("--positive-folder", dest='positive_folder')
    parser.add_argument("--negative-folder", dest='negative_folder')
    args = parser.parse_args()
    return args


#todo: pdf and zip files!

def create_toloka_pool(project_path, toloka_stream):
    logger = logging.getLogger("")
    with TRobotProject(logger, project_path, ROBOT_STEPS, None) as project:
        project.read_project()
        office_info = project.offices[0]
        toloka_stream.write("INPUT:url\tINPUT:file_link\tINPUT:file_extension\tINPUT:html\n")
        ec = TExternalConverters()
        cnt = 0
        all_files = 0
        for export_record in office_info.exported_files:
            all_files += 1
            sys.stderr.write("{}/{}\n".format(all_files, len(office_info.exported_files)))
            sys.stderr.flush()
            url = export_record['url']
            cached_file = export_record['cached_file']
            extension = TDownloadedFile(logger, url).file_extension
            temp_file = "dummy" + extension
            shutil.copy(cached_file, temp_file)
            html = ec.convert_to_html_with_soffice(temp_file)
            os.unlink(temp_file)
            if html is not None:
                html = html.replace("\t", " ").replace("\n", " ").replace("\r", " ")
                toloka_stream.write("\t".join((url, cached_file, extension, html)) + "\n\n")
                cnt += 1
        sys.stderr.write("written {} lines of of {}".format(cnt, all_files))


def copy_files(args, toloka_results):
    assert args.positive_folder is not None
    assert args.negative_folder is not None
    logger = logging.getLogger("")
    with TRobotProject(args.project, ROBOT_STEPS) as project:
        project.read_project()
        office_info = project.offices[0]
        index = 0
        domain = strip_html_url(office_info.morda_url)
        for export_record in office_info.exported_files:
            index += 1
            cached_file = export_record['cached_file']
            url = export_record['url']
            print ()
            extension = TDownloadedFile(logger, url).file_extension
            out_file = "{}_{}_{}{}".format(domain, index, int(time.time()), extension)
            tol_res = toloka_results.get(cached_file)
            if tol_res == "YES":
                folder = args.positive_folder
            elif tol_res == "NO":
                folder = args.negative_folder
            else:
                folder = None
            if folder is not None:
                out_file = os.path.join(folder, out_file)
                print ("{} -> {}".format(url, out_file))
                shutil.copy(cached_file, out_file)


if __name__ == "__main__":
    args = parse_args()
    if args.output_toloka is not None:
        with open(args.output_toloka, "w", encoding="utf8") as outf:
            create_toloka_pool(args, outf)
    else:
        results = dict()
        csv.field_size_limit(10000000)
        with open(args.input_assignments, "r", encoding="utf8") as inpf:
            for task in csv.DictReader(inpf, delimiter="\t", quotechar='"'):
                results[task['INPUT:file_link']] = task['OUTPUT:result']
        copy_files(args, results)