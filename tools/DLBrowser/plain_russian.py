import urllib.request
import sys
from urllib.parse import urlparse, quote_plus, urlencode, quote
import json
import time
import argparse


#======================= copy data from drop box ========================
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-corpus", dest='in_corpus', help ="coprus file",  default=None)
    parser.add_argument("--only-report", dest='only_report', action="store_true", default=False)
    parser.add_argument("--output-corpus", dest='out_corpus', help ="coprus file",  default=None)
    
    return parser.parse_args()


def get_metrics(text):
    data = urlencode({"text": text}, quote_via=quote).encode('latin')
    response = urllib.request.urlopen("http://api.plainrussian.ru/api/1.0/ru/measure/", data)
    html = response.read().decode("utf-8")
    return json.loads(html)

def avg(items):
    count = 0
    all_sum = 0.0
    for i in items:
        count += 1
        all_sum += i
    if count == 0:
        return -1
   
    return all_sum / count


if __name__ == "__main__":
    args = parse_args() 
    if args.in_corpus != None:
        with open(args.in_corpus, "r", encoding="utf8") as inpf:
            offices = json.load(inpf)
    else:
        offices = [{'filtered_texts':[]}]
        for filename in sys.stdin:
            with open (filename.strip(), "r", encoding="utf8") as inpf:
                text =  inpf.read()
            offices[0]['filtered_texts'].append({'text':text})

    if not args.only_report:
        for office in offices:
            print(office.get('office_name', ''))
            for t in office.get("filtered_texts", []):
                t['metrics'] = get_metrics (t['text'])


    if args.out_corpus != None:
        with open(args.out_corpus, "w", encoding="utf8") as outf:
            json.dump (offices, outf, indent=4, ensure_ascii=False)

    index_dc =  []
    index_ari  = []
    index_SMOG = []
    text_size = 0
    cnt = 0
    for office in offices:
        for t in office.get("filtered_texts", []):
            cnt += 1
            text_size += len(t['text'])
            metrics = t['metrics']
            if metrics['indexes']['index_dc'] > 0:
                index_dc.append(metrics['indexes']['index_dc'])
            if metrics['indexes']['index_ari'] > 0:
                index_ari.append(metrics['indexes']['index_ari'])
            if metrics['indexes']['index_SMOG'] > 0:
                index_SMOG.append(metrics['indexes']['index_SMOG'])

    print ("Count = {}".format(cnt))

    print ("avg index_dc: {}".format(avg(index_dc))) 
    print ("avg index_ari: {}".format(avg(index_ari))) 
    print ("avg index_SMOG: {}".format(avg(index_SMOG))) 
    print ("text_size: {}".format(text_size));
