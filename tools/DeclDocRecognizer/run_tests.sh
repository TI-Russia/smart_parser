cd  tests
rm *.json
for x in `ls * | grep -v json`; do
    bash ../dlrecognizer.sh $x  $x.json
done
cd -
#git diff tests
