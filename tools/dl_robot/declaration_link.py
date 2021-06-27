import re
from DeclDocRecognizer.document_types import SOME_OTHER_DOCUMENTS
from common.download import get_file_extension_only_by_headers
from common.primitives import normalize_and_russify_anchor_text
from common.http_request import THttpRequester
from common.link_info import TLinkInfo, check_sub_page_or_iframe
from common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION

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
    return re.search(ROLE_FIRST_WORDS_REGEXP, s, re.IGNORECASE)


def looks_like_a_document_link(logger, link_info: TLinkInfo):
    # check anchor text
    anchor_text_ru = normalize_and_russify_anchor_text(link_info.anchor_text)
    anchor_text_en = link_info.anchor_text.lower()
    if re.search('(скачать)|(загрузить)', anchor_text_ru) is not None:
        return True
    if anchor_text_en.find("download") != -1:
        return True
    target_url = ''
    if link_info.target_url is not None:
        target_url = link_info.target_url.lower()
    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if e == DEFAULT_HTML_EXTENSION:
            continue
        # mos.ru: anchor text is "[ docx/ 1.1Mb ]Сведения"
        if anchor_text_en.find(e[1:]) != -1:
            return True
        if target_url.endswith(e):
            return True

    # check url path or make http head request
    if target_url != "":
        if re.search('(docs)|(documents)|(files)|(download)', target_url):
            return True
        if target_url.endswith('html') or target_url.endswith('htm'):
            return False
        if target_url.endswith('.jpg') or target_url.endswith('.png'):
            return False
        try:
            # think that www.example.com/aaa/aa is always an html
            if link_info.url_query == "":
                return False
            ext = get_file_extension_only_by_headers(link_info.target_url)
            return ext != DEFAULT_HTML_EXTENSION and ext in ACCEPTED_DECLARATION_FILE_EXTENSIONS
        except THttpRequester.RobotHttpException as err:
            if err.count == 1:
                logger.error(err)
            return False

    return False


INCOME_URL_REGEXP = '(do[ck]?[hx]od)|(income)'


def url_features(url):
    income_url = False
    svedenija_url = False
    corrupt_url = False
    if url is not None:
        if re.search('(^sved)|(sveodoh)|(de[ck]lara)', url, re.IGNORECASE):
            svedenija_url = True
        if re.search(INCOME_URL_REGEXP, url, re.IGNORECASE):
            income_url = True
        if re.search('[ck]orrup', url, re.IGNORECASE):
            corrupt_url = True
    return income_url, svedenija_url, corrupt_url


def looks_like_a_declaration_link_without_cache(logger, link_info: TLinkInfo):
    # here is a place for ML
    anchor_text_russified = normalize_and_russify_anchor_text(link_info.anchor_text)
    page_html = normalize_and_russify_anchor_text(link_info.page_html)
    positive_case = None
    anchor_best_match = False
    if re.search('^((сведения)|(справк[аи])) о доходах', anchor_text_russified):
        anchor_best_match = True
        positive_case = "case 0"
    elif has_negative_words(anchor_text_russified):
        return False
    income_regexp = '(доход((ах)|(е)))|(коррупц)'
    sved_regexp = '(сведения)|(справк[аи])|(sveden)'
    svedenija_anchor = re.search(sved_regexp, anchor_text_russified) is not None or \
                       re.search(sved_regexp, link_info.anchor_text, re.IGNORECASE) is not None
    year_anchor = re.search('\\b20[0-9][0-9]\\b', anchor_text_russified) is not None
    income_page = re.search(income_regexp, page_html) is not None
    source_page_title_has_income_word = re.search(income_regexp, link_info.source_page_title) is not None
    income_anchor = re.search(income_regexp, anchor_text_russified) is not None
    role_anchor = is_public_servant_role(anchor_text_russified)
    document_url = None
    sub_page = check_sub_page_or_iframe(logger, link_info)
    income_url, svedenija_url, corrupt_url = url_features(link_info.target_url)
    if link_info.element_class is not None:
        if isinstance(link_info.element_class, list):
            for css_class_name in link_info.element_class:
                if re.search(INCOME_URL_REGEXP, css_class_name, re.IGNORECASE):
                    income_url = True

    if positive_case is None:
        if income_page or income_url:
            if svedenija_anchor or year_anchor or sub_page:
                positive_case = "case 1"
            else:
                if document_url is None:
                    document_url = looks_like_a_document_link(logger, link_info)  #lazy calculaiton since it has a time-consuming head http-request
                if document_url:
                    positive_case = "case 1"

    # http://arshush.ru/index.php?option=com_content&task=blogcategory&id=62&Itemid=72
    # "Сведения за 2018 год" - no topic word
    if positive_case is None:
        if svedenija_anchor or svedenija_url:
            if year_anchor:
                positive_case = "case 2"
            else:
                if document_url is None:
                    document_url = looks_like_a_document_link(logger, link_info)
                if document_url:
                    positive_case = "case 2"

    if positive_case is None:
        if (income_page or income_url) and role_anchor:
            positive_case = "case 3"

    if positive_case is None:
        if source_page_title_has_income_word and income_url:
            positive_case = "case 4"

    if positive_case is not None:
        weight = TLinkInfo.MINIMAL_LINK_WEIGHT
        if anchor_best_match:
            weight += TLinkInfo.BEST_LINK_WEIGHT
        if income_anchor:
            weight += TLinkInfo.BEST_LINK_WEIGHT
        if income_url:
            weight += TLinkInfo.BEST_LINK_WEIGHT
        if svedenija_anchor:
            weight += TLinkInfo.NORMAL_LINK_WEIGHT
        if svedenija_url:
            weight += TLinkInfo.NORMAL_LINK_WEIGHT
        if year_anchor:
            weight += TLinkInfo.TRASH_LINK_WEIGHT  # better than sub_page
        if income_page and weight > 0:
            weight += TLinkInfo.LINK_WEIGHT_FOR_INCREMENTING
        if corrupt_url and weight > 0:
            weight += TLinkInfo.LINK_WEIGHT_FOR_INCREMENTING
        all_features = (("income_page", income_page),
                        ("income_url", income_url),
                        ('income_anchor', income_anchor),
                        ('svedenija_anchor', svedenija_anchor),
                        ('svedenija_url', svedenija_url),
                        ("document_url", document_url),
                        ("sub_page", sub_page),
                        ("year_anchor", year_anchor),
                        ("corrupt_url", corrupt_url),
                        ('role_anchor', role_anchor),
                        ('anchor_best_match', anchor_best_match))

        all_features_str = ";".join(k for k, v in all_features if v)
        logger.debug("{}, weight={}, features: {}".format(positive_case, weight, all_features_str))
        link_info.weight = weight
        return True
    return False


DECLARATION_LINK_CACHE = dict()


def looks_like_a_declaration_link(logger, link_info: TLinkInfo):
    #return looks_like_a_declaration_link_without_cache(logger, link_info)
    global DECLARATION_LINK_CACHE
    if link_info.is_hashable():
        result = DECLARATION_LINK_CACHE.get(link_info.hash_by_target())
        if result is not None:
            return result
    result = looks_like_a_declaration_link_without_cache(logger, link_info)
    if link_info.is_hashable():
        DECLARATION_LINK_CACHE[link_info.hash_by_target()] = result
    return result


def check_sveden_url_sitemap_xml(url):
    features = url_features(url)

    if sum(features) > 1:
        return TLinkInfo.BEST_LINK_WEIGHT

    return TLinkInfo.MINIMAL_LINK_WEIGHT
