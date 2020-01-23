import ssl
import urllib.parse
import urllib.request
import json
import re
import shutil
from urllib.parse import urlparse, quote, unquote, urlunparse
import hashlib
from collections import defaultdict
import logging
import zipfile
import os

FILE_CACHE_FOLDER = "cached"
DEFAULT_HTML_EXTENSION = ".html"
DEFAULT_ZIP_EXTENSION = ".zip"
ACCEPTED_DECLARATION_FILE_EXTENSIONS = {'.doc', '.pdf', '.docx', '.xls', '.xlsx', '.rtf', '.zip', DEFAULT_HTML_EXTENSION}
UNKNOWN_PEOPLE_COUNT = -1
HEADER_MEMORY_CACHE = {}
HEADER_REQUEST_COUNT = defaultdict(int)

def is_html_contents(info):
    content_type = info.get('Content-Type', "text").lower()
    return content_type.startswith('text')


def make_http_request(url, method):
    o = list(urlparse(url)[:])
    if has_cyrillic(o[1]):
        o[1] = o[1].encode('idna').decode('latin')

    o[2] = unquote(o[2])
    o[2] = quote(o[2])
    url = urlunparse(o)
    context = ssl._create_unverified_context()
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    logger = logging.getLogger("dlrobot_logger")
    logger.debug("urllib.request.urlopen ({}) method={}".format(url, method))
    with urllib.request.urlopen(req, context=context, timeout=20.0) as request:
        data = '' if method == "HEAD" else request.read()
        info = request.info()
        headers = request.headers
        return info, headers, data


def request_url_headers (url):
    global HEADER_MEMORY_CACHE, HEADER_REQUEST_COUNT
    if url in HEADER_MEMORY_CACHE:
        return HEADER_MEMORY_CACHE[url]
    if HEADER_REQUEST_COUNT[url] >= 3:
        raise Exception("too many times to get headers that caused exceptions")

    HEADER_REQUEST_COUNT[url] += 1
    _, headers, _ = make_http_request(url, "HEAD")
    HEADER_MEMORY_CACHE[url] = headers
    return headers


def find_simple_js_redirect(data):
    res = re.search('((window|document).location\s*=\s*[\'"]?)([^"\']+)([\'"]?\s*;)', data)
    if res:
        url = res.group(3)
        return url
    return None


def has_cyrillic(text):
    return bool(re.search('[Ёёа-яА-Я]', text))


def get_site_domain_wo_www(url):
    url = "http://" + url.split("://")[-1]
    domain = urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[len('www.'):]
    return domain


def convert_html_to_utf8(data, url_info):
    encoding = url_info.get('charset')
    if encoding is None:
        match = re.search('charset=([^"\']+)', data.decode('latin', errors="ignore"))
        if match:
            encoding = match.group(1)
        else:
            raise ValueError('unable to find encoding')
    if encoding.lower().startswith('cp-'):
        encoding = 'cp' + encoding[3:]

    return data.decode(encoding, errors="ignore")


def download_with_urllib (url, search_for_js_redirect=True):
    info, headers, data = make_http_request(url, "GET")

    try:
        if is_html_contents(info):
            if search_for_js_redirect:
                try:
                    redirect_url = find_simple_js_redirect(data.decode('latin', errors="ignore"))
                    if redirect_url is not None and redirect_url != url:
                        return download_with_urllib(redirect_url, search_for_js_redirect=False)
                except Exception as err:
                    pass

    except AttributeError:
        pass
    return data, info


def read_cache_file(localfile):
    with open(localfile, "rb") as f:
        return f.read()

def read_url_info_from_cache(url):
    localfile = get_local_file_name_by_url(url)
    if not os.path.exists(localfile):
        return {}
    info_file = localfile + ".headers"
    with open(info_file, "r", encoding="utf8") as inf:
        return json.loads(inf.read())


def write_cache_file(localfile, info_file, info, data):
    with open(localfile, "wb") as f:
        f.write(data)

    if info is not None:
        with open(info_file, "w", encoding="utf8") as f:
            url_info = dict()
            if hasattr(info, "_headers"):
                url_info['headers'] = dict(info._headers)
            else:
                url_info['headers'] = dict()
            url_info['charset'] = info.get_content_charset()
            f.write(json.dumps(url_info, indent=4, ensure_ascii=False))
    return data


def url_to_localfilename (url):
    localfile = url
    if localfile.startswith('http://'):
        localfile = localfile[7:]
    if localfile.startswith('https://'):
        localfile = localfile[8:]
    localfile = localfile.replace(':', '_')
    localfile = localfile.replace('/', '\\')
    localfile = localfile.replace('&', '_')
    localfile = localfile.replace('=', '_')
    localfile = localfile.replace('?', '_')
    if len(localfile) > 64:
        localfile = localfile[0:64] + "_" + hashlib.md5(url.encode('utf8',  errors="ignore")).hexdigest()
    return localfile



def save_download_file(filename):
    global FILE_CACHE_FOLDER
    download_folder = os.path.join(FILE_CACHE_FOLDER, "downloads")
    if not os.path.exists(download_folder):
        os.mkdir(download_folder)
    assert (os.path.exists(filename))

    with open(filename, "rb") as f:
        hashcode = hashlib.sha256(f.read()).hexdigest()
    extension = os.path.splitext(filename)[1]
    save_filename = os.path.join(download_folder, hashcode + extension)
    if os.path.exists(save_filename):
        logger = logging.getLogger("dlrobot_logger")
        logger.debug("replace existing {0}".format(save_filename))
        os.remove(save_filename)
    os.rename(filename, save_filename)
    return save_filename


def get_local_file_name_by_url(url):
    global FILE_CACHE_FOLDER
    if not os.path.exists(FILE_CACHE_FOLDER):
        os.mkdir(FILE_CACHE_FOLDER)

    localfile = url_to_localfilename(url)

    localfile = os.path.join(FILE_CACHE_FOLDER, localfile)
    if not localfile.endswith('html') and not localfile.endswith('htm'):
        localfile += "/index.html"
    if not os.path.exists(os.path.dirname(localfile)):
        os.makedirs(os.path.dirname(localfile))
    return localfile


def download_with_cache(url, convert_to_utf8=False):
    localfile = get_local_file_name_by_url(url)
    info_file = localfile + ".headers"
    if os.path.exists(localfile):
        data = read_cache_file(localfile)
    else:
        data, info = download_with_urllib(url)
        if len(data) == 0:
            return ""
        write_cache_file(localfile, info_file, info, data)

    info = read_url_info_from_cache(url) # reread in a different format
    if convert_to_utf8:
        return convert_html_to_utf8(data, info)
    else:
        return data

def get_extenstion_by_content_type(content_type):
    if content_type.startswith("text"):
        return DEFAULT_HTML_EXTENSION
    elif content_type.startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
        return ".xlsx"
    elif content_type.startswith("application/vnd.openxmlformats-officedocument"):
        return ".docx"
    elif content_type.find("ms-word") != -1:
        return ".doc"
    elif content_type.startswith("application/msword"):
        return ".doc"
    elif content_type.startswith("application/rtf"):
        return ".rtf"
    elif content_type.startswith("application/excel"):
        return ".xls"
    elif content_type.startswith("application/vnd.ms-excel"):
        return ".xls"
    elif content_type.startswith("application/pdf"):
        return ".pdf"
    elif content_type.startswith("application/zip"):
        return ".zip"
    elif content_type.startswith("application/rss+xml"):
        return ".some_xml"
    elif content_type.startswith("application/xml"):
        return ".some_xml"
    elif content_type.startswith("application/"):
        return ".some_application_format"
    elif content_type.startswith("image/"):
        return ".some_image_format"
    elif content_type.startswith("audio/"):
        return ".some_audio_format"
    elif content_type.startswith("video/"):
        return ".some_video_format"
    else:
        return DEFAULT_HTML_EXTENSION


def get_file_extension_by_cached_url(url):
    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if url.lower().endswith(e):
            return e

    content_type = read_url_info_from_cache(url).get('headers', {}).get('Content-Type', "text")
    return get_extenstion_by_content_type(content_type)


def get_file_extension_by_url(url):
    headers = request_url_headers(url)
    ext = get_extenstion_by_content_type(headers.get('Content-Type', "text"))
    return ext


def process_smart_parser_json(json_file):
    with open(json_file, "r", encoding="utf8") as inpf:
        smart_parser_json = json.load(inpf)
        people_count = len(smart_parser_json.get("persons", []))
    os.remove(json_file)
    return people_count


def get_people_count_from_smart_parser(smart_parser_binary, inputfile):
    people_count = UNKNOWN_PEOPLE_COUNT
    if smart_parser_binary == "none":
        return people_count
    if inputfile.endswith("pdf"): # cannot process new pdf without conversion
        return people_count
    logger = logging.getLogger("dlrobot_logger")
    cmd = "{} -skip-relative-orphan -skip-logging  -adapter prod -fio-only {}".format(smart_parser_binary, inputfile)
    logger.debug(cmd)
    os.system(cmd)
    json_file = inputfile + ".json"
    if os.path.exists(json_file):
        people_count = process_smart_parser_json(json_file)
    else:
        sheet_index = 0
        while True:
            json_file = "{}_{}.json".format(inputfile, sheet_index)
            if not os.path.exists(json_file):
                break
            if people_count == UNKNOWN_PEOPLE_COUNT:
                people_count = 0
            people_count += process_smart_parser_json(json_file)
            sheet_index += 1
    return people_count

def unzip_one_file(input_file, main_index, outfolder):
    global ACCEPTED_DECLARATION_FILE_EXTENSIONS
    zip_file = zipfile.ZipFile(input_file)
    index = 0
    for filename in zip_file.namelist():
        _, file_extension = os.path.splitext(filename)
        file_extension = file_extension.lower()
        if file_extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
            continue
        zip_file.extract(filename, outfolder)
        old_file_name = os.path.join(outfolder, filename)
        new_file_name = os.path.join(outfolder, "{}_{}{}".format(main_index, index, file_extension))
        os.rename(old_file_name,  new_file_name)
        yield new_file_name
        index += 1
    zip_file.close()


def export_one_file(smart_parser_binary, url, uniq_files, index, infile, extension, office_folder, export_files):
    global ACCEPTED_DECLARATION_FILE_EXTENSIONS
    outpath = os.path.join(office_folder, str(index) + extension)
    if not os.path.exists(os.path.dirname(outpath)):
        os.makedirs(os.path.dirname(outpath))
    if not os.path.exists(infile) or extension not in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        return UNKNOWN_PEOPLE_COUNT
    if extension == DEFAULT_ZIP_EXTENSION:
        people_count_sum = UNKNOWN_PEOPLE_COUNT
        for filename in unzip_one_file(infile, index, office_folder):
            with open(filename, "rb") as f:
                sha256hash = hashlib.sha256(f.read()).hexdigest()
            if sha256hash not in uniq_files:
                people_count = get_people_count_from_smart_parser(smart_parser_binary, filename)
                export_record = {
                    "url": url,
                    "sha256": sha256hash,
                    "infile": infile,
                    "people_count": people_count,
                    "outpath": filename
                }
                export_files.append(export_record)
            else:
                people_count = uniq_files[sha256hash]['people_count']
            if people_count > 0:
                if people_count_sum == UNKNOWN_PEOPLE_COUNT:
                    people_count_sum = 0
                people_count_sum += people_count

        return people_count_sum
    else:
        with open(infile, "rb") as f:
            sha256hash = hashlib.sha256(f.read()).hexdigest()
        if sha256hash not in uniq_files:
            shutil.copyfile(infile, outpath)
            people_count = get_people_count_from_smart_parser(smart_parser_binary, outpath)
            export_record = {
                "url": url,
                "sha256": sha256hash,
                "outpath": outpath,
                "infile": infile,
                "people_count": people_count
            }
            uniq_files[sha256hash] = export_record
            export_files.append(export_record)
            return people_count
        else:
            return uniq_files[sha256hash]['people_count']



def export_files_to_folder(offices, smart_parser_binary, outfolder):
    logger = logging.getLogger("dlrobot_logger")
    for office_info in offices:
        office_folder = url_to_localfilename(office_info.morda_url)
        office_folder = os.path.join(outfolder, office_folder)
        if os.path.exists(office_folder):
            shutil.rmtree(office_folder)
        index = 0
        uniq_files = dict()
        export_files = list()
        last_step_urls = office_info.robot_steps[-1].step_urls
        logger.debug("process {} urls in last step".format(len(last_step_urls)))
        for url in last_step_urls:
            extension = get_file_extension_by_cached_url(url)
            infile = get_local_file_name_by_url(url)
            office_info.url_nodes[url].people_count = \
                export_one_file (smart_parser_binary, url, uniq_files, index, infile, extension, office_folder, export_files)
            index += 1

        for url_info in office_info.url_nodes.values():
            for d in url_info.downloaded_files:
                infile = d['downloaded_file']
                extension = os.path.splitext(infile)[1]
                d['people_count'] = \
                    export_one_file(smart_parser_binary, "", uniq_files, index, infile, extension, office_folder, export_files)
                index += 1
        office_info.exported_files = export_files
        logger.info("exported {0} files to {1}".format(len(export_files), office_folder))
