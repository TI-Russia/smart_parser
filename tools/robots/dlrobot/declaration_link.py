import re
import logging
from DeclDocRecognizer.document_types import SOME_OTHER_DOCUMENTS
from robots.common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION
from robots.common.download import get_file_extension_only_by_headers
from robots.common.primitives import normalize_and_russify_anchor_text, check_sub_page_or_iframe
from robots.common.http_request import RobotHttpException
from robots.common.find_link import TLinkInfo

NEGATIVE_WORDS = [
    'координат',  'заседании',
    #'должност', # замещающих должности
    'выборы',    'памятка',    'доклад',
    'конкурс',    'пресс-релиз',    'правила',
    'положение',    'методические',    'заявление',
    'схема',    'концепция',    'доктрина',
    'технические',    '^федеральный',    '^историческ',
    '^закон',    'новости', "^формы", "обратная", "обращения",
    "^перечень", "прочие", "слабовидящих",
    # пробуем:
    "документация",
] + ['^.{{0,10}}{}'.format(t) for t in SOME_OTHER_DOCUMENTS]
# document type (SOME_OTHER_DOCUMENTS)  (указ, утверждена) can be inside the title, for example:
#сведения о доходах, об имуществе и обязательствах имущественного характера, представленные руководителями федеральных государственных учреждений, находящихся в ведении министерства здравоохранения российской федерации за отчетный период с 1 января 2012 года по 31 декабря 2012 года, подлежащих размещению на официальном сайте министерства здравоохранения российской федерации в соответствии порядком размещения указанных сведений на официальных сайтах федеральных государственных органов, утвержденным указом президента российской федерации от 8 июля 2013 г. № 613
# but not in the beginning (first 10 chars)

NEGATIVE_REGEXP = re.compile("|".join(list("({})".format(x) for x in NEGATIVE_WORDS)))


def has_negative_words(anchor_text):
    global NEGATIVE_REGEXP
    return NEGATIVE_REGEXP.search(anchor_text) is not None

ROLE_FIRST_WORDS = [
    "администратор", "ведущий", "врио", "генеральный", "глава", "главный",
    "государственная", "государственный", "директор", "должность", "доцент",
    "заведующая", "заведующий", "зам", "заместитель", "инспектор", "исполняющий", "консультант",
    "контролер", "начальник", "первый", "полномочный", "помощник",
    "поректор", "председатель", "представитель", "проректор",
    "ректор", "референт", "руководитель", "секретарь", "советник",
    "специалист", "специальный", "старший", "статс", "судья",
    "технический", "уполномоченный", "управляющий", "финансовый",
    "член", "экономист", "юрисконсульт"
]
ROLE_FIRST_WORDS_REGEXP = "|".join(("(^{})".format(x) for x in ROLE_FIRST_WORDS))


def is_public_servant_role(s):
    global ROLE_FIRST_WORDS_REGEXP
    return re.search(ROLE_FIRST_WORDS_REGEXP, s, re.IGNORECASE)

def looks_like_a_document_link(link_info: TLinkInfo):
    global ACCEPTED_DECLARATION_FILE_EXTENSIONS

    # check anchor text
    anchor_text_ru = normalize_and_russify_anchor_text(link_info.anchor_text)
    anchor_text_en = link_info.anchor_text.lower()
    if re.search('(скачать)|(загрузить)', anchor_text_ru) is not None:
        return True
    if anchor_text_en.find("download") != -1:
        return True
    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if e == DEFAULT_HTML_EXTENSION:
            continue
        # mos.ru: anchor text is "[ docx/ 1.1Mb ]Сведения"
        if anchor_text_en.find(e[1:]) != -1:
            return True

    # check url path or make http head request
    if link_info.target_url is not None:
        target = link_info.target_url.lower()
        if re.search('(docs)|(documents)|(files)|(download)', target):
            return True
        if target.endswith('html') or target.endswith('htm'):
            return False
        if target.endswith('.jpg') or target.endswith('.png'):
            return False
        try:
            ext = get_file_extension_only_by_headers(link_info.target_url)
            return ext != DEFAULT_HTML_EXTENSION and ext in ACCEPTED_DECLARATION_FILE_EXTENSIONS
        except RobotHttpException as err:
            if err.count == 1:
                logging.getLogger("dlrobot_logger").error(err)
            return False

    return False


def looks_like_a_declaration_link(link_info: TLinkInfo):
    # here is a place for ML
    anchor_text = normalize_and_russify_anchor_text(link_info.anchor_text)
    if re.search('^((сведения)|(справк[аи])) о доходах', anchor_text):
        link_info.weight = TLinkInfo.BEST_LINK_WEIGHT
        logging.getLogger("dlrobot_logger").debug("case 0, weight={}, features: 'сведения о доходах'".format(link_info.weight))
        return True
    page_html = normalize_and_russify_anchor_text(link_info.page_html)
    if has_negative_words(anchor_text):
        return False
    income_regexp = '(доход((ах)|(е)))|(коррупц)'

    good_doc_type_anchor = re.search('(сведения)|(справк[аи])', anchor_text) is not None
    year_found_anchor = re.search('\\b20[0-9][0-9]\\b', anchor_text) is not None
    income_page = re.search(income_regexp, page_html) is not None
    income_anchor = re.search(income_regexp, anchor_text) is not None
    role_anchor = is_public_servant_role(anchor_text)
    document_link = None
    sub_page = check_sub_page_or_iframe(link_info)
    income_path = False
    good_doc_type_path = False
    if link_info.target_url is not None:
        target = link_info.target_url.lower()
        if re.search('(^sved)|(sveodoh)', target):
            good_doc_type_path = True
        if re.search('(do[ck]?[hx]od)|(income)', target):
            income_path = True
    positive_case = None

    if positive_case is None:
        if income_page or income_path:
            if good_doc_type_anchor or year_found_anchor or sub_page:
                positive_case = "case 1"
            else:
                if document_link is None:
                    document_link = looks_like_a_document_link(link_info)  #lazy calculaiton since it has a time-consuming head http-request
                if document_link:
                    positive_case = "case 1"

    # http://arshush.ru/index.php?option=com_content&task=blogcategory&id=62&Itemid=72
    # "Сведения за 2018 год" - no topic word
    if positive_case is None:
        if good_doc_type_anchor or good_doc_type_path:
            if year_found_anchor:
                positive_case = "case 2"
            else:
                if document_link is None:
                    document_link = looks_like_a_document_link(link_info)
                if document_link:
                    positive_case = "case 2"

    if positive_case is None:
        if (income_page or income_path) and role_anchor:
            positive_case = "case 3"

    if positive_case is not None:
        weight = TLinkInfo.MINIMAL_LINK_WEIGHT
        if income_anchor:
            weight += TLinkInfo.BEST_LINK_WEIGHT
        if income_path:
            weight += TLinkInfo.BEST_LINK_WEIGHT
        if good_doc_type_anchor:
            weight += TLinkInfo.NORMAL_LINK_WEIGHT
        if good_doc_type_path:
            weight += TLinkInfo.NORMAL_LINK_WEIGHT
        if year_found_anchor:
            weight += TLinkInfo.TRASH_LINK_WEIGHT  # better than sub_page

        all_features = (("income_page", income_page), ("income_path", income_path), ('income_anchor', income_anchor),
                        ('good_doc_type_anchor', good_doc_type_anchor), ('good_doc_type_path', good_doc_type_path),
                        ("document_link", document_link),
                        ("sub_page", sub_page),
                        ("year_found_anchor", year_found_anchor), ('role_anchor', role_anchor))

        all_features_str = ";".join(k for k, v in all_features if v)
        logging.getLogger("dlrobot_logger").debug("{}, weight={}, features: {}".format(positive_case, weight, all_features_str))
        link_info.weight = weight
        return True
    return False