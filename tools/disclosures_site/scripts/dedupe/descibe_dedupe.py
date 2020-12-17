import dedupe
import sys


def describe_dedupe(dedupe, outp):
    outp.write("Dedupe blocking predicates:\n")
    for p in dedupe.predicates:
        outp.write("\t" + repr(p) + "\n")
    outp.write("ML type: {}\n".format(type(dedupe.classifier)))
    outp.write("ML weights:" + "\n")
    if hasattr(dedupe.classifier, "weights"):
        weights = dedupe.classifier.weights
    else:
        weights = dedupe.classifier.feature_importances_
    weights_str = "\n".join(map(repr, zip(dedupe.data_model.primary_fields, weights)))
    outp.write(weights_str + "\n")


if __name__ == '__main__':
    sys.stdout.write("load {}".format(sys.argv[1]))
    with open(sys.argv[1], 'rb') as sf:
        describe_dedupe(dedupe.StaticDedupe(sf), sys.stdout)

