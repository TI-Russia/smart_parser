import re

GEO_LEAF_WORDS = {"поселение", "поселения", "район", "районы", "улус", "улусы", "округ"}

#сельские и городские поселения
def has_geo_leaf_word_in_beginning(text, max_index=5):
    words = re.split('[\s,"]', text.lower())
    for w in words[:max_index]:
        if w is not None and w in GEO_LEAF_WORDS:
            return True
    return False
