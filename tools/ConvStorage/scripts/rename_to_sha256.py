import os
import hashlib
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
            with open(pdf_file, "rb") as f:
                sha256hash = hashlib.sha256(f.read()).hexdigest()
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
