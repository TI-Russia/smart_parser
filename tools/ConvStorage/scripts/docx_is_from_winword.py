import zipfile
import sys
if __name__ == '__main__':
    input_file = sys.argv[1]
    assert input_file.endswith(".docx")
    exit_code = 1
    try:
        with zipfile.ZipFile(input_file) as zf:
            for zipinfo in zf.infolist():
                if zipinfo.filename.endswith('webSettings.xml'):
                    print("{} is from winword 2010".format(input_file))
                    exit_code = 0
                    break
        sys.exit(exit_code)
    except Exception as exp:
        sys.stderr.write("exp={}\n".format(exp))
        sys.exit(1)