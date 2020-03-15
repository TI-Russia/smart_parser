from lxml import etree
import os
PATH = os.path.dirname( os.path.realpath(__file__) )
HFT_FILE = 'test.hft'

if __name__ == '__main__':
    tree = etree.parse(HFT_FILE)
    root = tree.getroot()
    update_count = 0
    for x in root.iter('{http://www.abbyy.com/HotFolder/Engine/TaskAddEmagesStep}addImages'):
        folder = os.path.join(PATH, "pdf.ocr")
        if not os.path.exists(folder):
            os.mkdir(folder)
        print("set input folder to {}".format(folder))
        x.set('folderPath', folder)
        update_count += 1
    assert update_count == 1

    update_count = 0
    for x in root.iter('{http://www.abbyy.com/HotFolder/Engine/SaveStep}step'):
        folder = os.path.join(PATH, "pdf.ocr.out")
        if not os.path.exists(folder):
            os.mkdir(folder)
        print ("set export folder to {}".format(folder))
        x.set('savePath', folder)
        update_count += 1
    assert  update_count == 1

    tree.write(HFT_FILE)