from iso639 import languages

united_nations_style_languages = {'en', 'de', 'fr', 'es', 'pt', '中文', 'عربية'}

popular_languages_in_russian = {"fijian", "испанский", "сербский (кириллица)", "filipino",
    "итальянский",  "сербский (латиница)", "malagasy", "кантонский (традиционное письмо)",
    "словацкий", "samoan", "каталанский", "словенский",
    "tahitian", "керетарский отоми", "суахили", "tongan",
    "китайский традиционный",  "тайский", "английский",
    "китайский упрощенный",  "турецкий", "арабский", "клингонский",
    "украинский", "африкаанс", "корейский", "урду",
    "болгарский",  "латышский", "финский", "боснийский (латиница)", "литовский",
    "французский",  "валлийский", "малайский", "хинди", "венгерский", "мальтийский",
    "хмонг дау",  "вьетнамский", "немецкий", "хорватский", "гаитянский креольский",
    "норвежский", "чешский", "голландский", "персидский", "шведский",
    "греческий"
}


def is_human_language(l):
    l = l.lower()
    if l in united_nations_style_languages:
        return True
    if l in popular_languages_in_russian:
        return True
    if len(l) == 3:
        try:
            if languages.get(part3=l) is not None:
                return True
        except Exception as exp:
            pass
    return False
