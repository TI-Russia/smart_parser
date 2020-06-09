import os
import argparse
import time


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr-input-folder", dest='ocr_input_folder', required=False, default="pdf.ocr")
    parser.add_argument("--ocr-output-folder", dest='ocr_output_folder', required=False, default="pdf.ocr.out")
    parser.add_argument("--expecting-files-count", dest='files_count', required=True, type=int)
    return parser.parse_args()


if __name__ == '__main__':
    files_count = 0
    while True:
        time.sleep(10)
        for x in os.listdir(args.ocr_input_folder):
            with os.path.join(args.ocr_output_folder, x + ".docx") as out:
                out.write("created bny ocr monkey")
            os.unlink(os.path(args.ocr_input_folder, x))
            files_count += 1
            if files_count >= args.files_count:
                break