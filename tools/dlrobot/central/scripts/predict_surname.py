from pylem import MorphLanguage, MorphanHolder, LemmaInfo

def find_dict_surname(holder, w):
    for l in holder.lemmatize(w):
        if not l.predicted and 'surname' in l.morph_features:
            return True
    return False

def find_surname_in_nominative(holder, w):
    for l in holder.lemmatize(w):
        if l.predicted and 'surname' in l.morph_features and 'nom' in l.morph_features and 'sg' in l.morph_features:
            return l.predicted_by
    return None


def main():
    holder = MorphanHolder(MorphLanguage.Russian)
    r = find_dict_surname(holder, "Иванов")
    assert r
    with open("surnames.txt") as inp:
        for line in inp:
            surname = line.strip()
            if find_dict_surname(holder, surname):
                print ("{} surname is in dictionary".format(surname))
            else:
                l = find_surname_in_nominative(holder, surname)
                if l is not None:
                    print("{} surname predicted by a similar surname ({})".format(surname, l))
                else:
                    print("{} surname unknown".format(surname))

if __name__ == "__main__":
    main()
