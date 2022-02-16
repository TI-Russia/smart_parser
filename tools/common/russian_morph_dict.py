from pylem import MorphanHolder, MorphLanguage, LemmaInfo

RUSSIAN_MORPH_DICT = MorphanHolder(MorphLanguage.Russian)


class TRussianDictWrapper:
    @staticmethod
    def get_all_lemmas(w):
        lemm_info: LemmaInfo
        for lemm_info in RUSSIAN_MORPH_DICT.lemmatize(w):
            yield lemm_info.lemma, lemm_info.word_weight

    @staticmethod
    def is_morph_surname_not_predicted(w):
        lemm_info: LemmaInfo
        for lemm_info in RUSSIAN_MORPH_DICT.lemmatize(w):
            if not lemm_info.predicted and 'surname' in lemm_info.morph_features:
                return True
        return False

    @staticmethod
    def get_max_word_weight(word_list):
        lemm_info: LemmaInfo
        return max(lemm_info.word_weight for w in word_list for lemm_info in RUSSIAN_MORPH_DICT.lemmatize(w))

    @staticmethod
    def is_morph_first_name(w):
        lemm_info: LemmaInfo
        for lemm_info in RUSSIAN_MORPH_DICT.lemmatize(w):
            if not lemm_info.predicted and 'name' in lemm_info.morph_features and 'poss' not in lemm_info.morph_features:
                return True
        return False

    @staticmethod
    def is_morph_animative_noun(w):
        lemm_info: LemmaInfo
        for lemm_info in RUSSIAN_MORPH_DICT.lemmatize(w):
            if lemm_info.lemma == "ВЕДУЩИЙ":
                continue
            if 'name' in lemm_info.morph_features or 'surname' in lemm_info.morph_features:
                continue
            if not lemm_info.predicted and lemm_info.part_of_speech == 'N' and  'anim' in lemm_info.morph_features:
                return True
        return False

    @staticmethod
    def is_morph_surname_or_predicted(w):
        if w.lower() == "машина":
            return False
        lemm_info: LemmaInfo
        for lemm_info in RUSSIAN_MORPH_DICT.lemmatize(w):
            if lemm_info.predicted or 'surname' in lemm_info.morph_features:
                return True
        return False

    @staticmethod
    def is_morph_surname(w):
        if w.lower() == "машина":
            return False
        lemm_info: LemmaInfo
        for lemm_info in RUSSIAN_MORPH_DICT.lemmatize(w):
            if 'surname' in lemm_info.morph_features:
                return True
        return False

    @staticmethod
    def is_in_dictionary(w):
        return RUSSIAN_MORPH_DICT.is_in_dictionary(w)
