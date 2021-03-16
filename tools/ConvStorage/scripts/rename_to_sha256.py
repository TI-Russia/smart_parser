from common.primitives import  build_dislosures_sha256_by_file_data

import os
import sys

if __name__ == '__main__':
    folder = sys.argv[1]
    for x in os.listdir(folder):
        if x.endswith(".pdf") and len(x) < 20:
            pdf_file = os.path.join(folder, x)
            docx_file = os.path.join(folder, x + ".docx")
            if not os.path.exists(docx_file):
                sys.stderr.write("cannot find {}\n".format(docx_file))
                sys.stderr.write("delete {}\n".format(pdf_file))
                os.unlink(pdf_file)
                continue
            sha256hash = build_dislosures_sha256_by_file_data(pdf_file)
            new_pdf_file = os.path.join(folder, sha256hash + ".pdf")
            if os.path.exists(new_pdf_file):
                sys.stderr.write("{} already exists, skip renaming\n".format(pdf_file))
                sys.stderr.write("delete {}\n".format(pdf_file))
                os.unlink(pdf_file)
                sys.stderr.write("delete {}\n".format(docx_file))
                os.unlink(docx_file)
                continue

            sys.stderr.write("rename {} to {}\n".format(pdf_file, new_pdf_file))
            os.rename(pdf_file, new_pdf_file)
            os.rename(docx_file, new_pdf_file + ".docx")
