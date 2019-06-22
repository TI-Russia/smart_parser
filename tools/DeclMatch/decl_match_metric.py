import json
import argparse

class TMatchInfo:

    def __init__(self):
        self.true_positive = []
        self.false_positive = []
        self.false_negative = []
        self.f_score= 1.0

    def dump_comparings(self, input_id, worker_id, input, title, errors):
        for x in input:
            errors.append("\t".join((input_id, worker_id, title, x)))

    def dump(self, input_id, worker_id, errors):
        self.dump_comparings(input_id, worker_id, self.true_positive, "TP", errors)
        self.dump_comparings(input_id, worker_id, self.false_positive, "FP", errors)
        self.dump_comparings(input_id, worker_id, self.false_negative, "FN", errors)

    def dump_type_errors(self, input, title, errors):
        for x in input:
            errors.append("\t".join((title, x)))

    def dump_errors(self):
        errors = []
        self.dump_type_errors(self.false_positive, "FP", errors)
        self.dump_type_errors(self.false_negative, "FN", errors)
        return errors


def read_field(dct, field_name):
    value = dct.get(field_name)
    if value is None:
        return value
    value = str(value)
    value = value.strip("\n \r\t")
    value = value.replace(" ", "")
    value = value.replace(u" ", "")
    value = value.replace("\n", "")
    value = value.lower()
    if value.endswith(u"(собственность)"):
        value = value[0:-len(u"(собственность)")]
    if value.endswith(u"(общаясобственность)"):
        value = value[0:-len(u"(общаясобственность)")]


    if field_name == "own_type":
        if value == u"индивидуальная":
            value = u"всобственности"
    if value.startswith(u"долевая1/"):
        value = value[len(u"долевая"):]
    if value.startswith('1/') and value[2:].isdigit():
        value = str(1/int(value[2:]))

    return value

def  check_equal_value(d1, d2, field_name):
    v1 = read_field(d1, field_name)
    v2 = read_field(d2, field_name)
    if v1 == v2:
        return (True, v1, v2)
    if v1 is None or v2 is None:
        return (False, v1, v2)
    try:
        f1 = float(v1.replace(",", "."))
        f2 = float(v2.replace(",", "."))
        if f1 == f2:
            return True, v1, v2
    except:
        pass
    return (False, v1, v2)

def check_field (person1, person2, parent_field, field_name, match_info):
    (result, value1, value2) = check_equal_value(person1, person2, field_name)
    if not result:
        if value2 is not None:
            match_info.false_positive.append(parent_field + "/" + field_name)
        if value1 is not None:
            match_info.false_negative.append(parent_field + "/" + field_name)
        return False
    else:
        if value1 is  not None:
            match_info.true_positive.append(parent_field + "/" + field_name)
        return True


def get_property(person, field_name, relative):
    for p in person.get(field_name, []):
        if p.get('relative') == relative:
            return p
    return {}


def check_incomes_or_auto(person1, person2, field_name, check_field_name, match_info):
    v1 = get_property(person1, field_name, None)
    v2 = get_property(person2, field_name, None)
    check_field (v1, v2, field_name + "/relative=null", check_field_name, match_info)

    relative = u"Супруг(а)"
    v1 = get_property(person1, field_name, relative)
    v2 = get_property(person2, field_name, relative)
    check_field (v1, v2, field_name + "/" + relative, check_field_name, match_info)


def are_equal_realty(p1, p2):
    return ( check_equal_value(p1, p2, "text")[0] and
             check_equal_value(p1, p2, "square")[0] and
             check_equal_value(p1, p2, "relative")[0] and
            # to do check county
             check_equal_value(p1, p2, "share_amount")[0] and
             check_equal_value(p1, p2, "own_type")[0]);

def describe_realty(p):
    return u"real estate {0}, {1}, {2}, {3}, {4} ".format(
        p.get("text").replace("\n", "\\n"), 
        p.get("square"), 
        p.get("own_type"), 
        p.get("relative"),
        p.get("share_amount"))

def check_realties(realties1, realties2, match_info):
    used = set()
    for p1 in realties1:
        found = False
        for i in range(len(realties2)):
            p2 = realties2[i]
            if i not in used and are_equal_realty(p1, p2):
                found = True
                used.add( i )
                match_info.true_positive.append (describe_realty(p1))
                break
        if not found:
            match_info.false_negative.append(describe_realty(p1))
    for i in range(len(realties2)):
        if i not in used:
            match_info.false_positive.append(describe_realty(realties2[i]))


def calc_decl_match_one_pair(json1, json2):
    match_info = TMatchInfo()
    if len(json1['persons']) == 0 and len(json2['persons']) == 0:
        match_info.f_score = 1.0
        return match_info
    elif len(json1['persons']) == 0 or len(json2['persons']) == 0:
        match_info.f_score = 0
        return match_info
    person1 = json1['persons'][0]
    person2 = json2['persons'][0]
    person_info_1 = person1.get('person', {})
    person_info_2 = person2.get('person', {})
    if not check_field(person_info_1, person_info_2,  "person",  "name_raw", match_info):
        match_info.f_score = 0
        return match_info
    check_field(person_info_1, person_info_2, "person", "role", match_info)
    check_field(person_info_1, person_info_2, "person", "department", match_info)
    check_field(person1, person2, "", "year", match_info)
    check_incomes_or_auto(person1, person2, "incomes", "size", match_info)
    check_incomes_or_auto(person1, person2, "vehicles", "text", match_info)
    check_realties(person1.get('real_estates', []), person2.get('real_estates', []), match_info)
    tp = len(match_info.true_positive)
    fp = len(match_info.false_positive)
    fn = len(match_info.false_negative)
    prec = tp /  (tp + fp + 0.0000001)
    recall = tp / (tp + fn + 0.0000001)
    match_info.f_score = 2 * prec * recall / (prec + recall)
    return match_info


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('json', nargs='+')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    j1 = None
    j2 = None
    with open (args.json[0], "r", encoding="utf8") as f1:
        j1 = json.load(f1)
    with open (args.json[1], "r", encoding="utf8") as f2:
        j2 = json.load(f2)
    match_info = calc_decl_match_one_pair(j1,  j2)
    errors = []
    match_info.dump("","", errors)
    for e in errors:
        print (e)