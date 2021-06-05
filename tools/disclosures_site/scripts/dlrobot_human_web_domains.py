from declarations.input_json import TSourceDocument, TDlrobotHumanFile
import sys

if __name__ == '__main__':
    dlrobot_human = TDlrobotHumanFile(sys.argv[1])
    value: TSourceDocument
    for key, value in dlrobot_human.document_collection.items():
        print ("{}\t{}".format(key, value.get_web_site()))