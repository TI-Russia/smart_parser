#1. Download and  unpack pywikibot to core follo https://www.mediawiki.org/wiki/Manual:Pywikibot/Installation
wget https://pywikibot.toolforge.org/core_stable.tar.gz
tar xfz core_stable.tar.gz
mv core_stable pywikibot
cd core_stable

python pwb.py generate_user_files
# Select family of sites: 13
# select language code: wikidata
#user name Declaratorbot
#password in password storage
python3  pwb.py login
 
#3. https://www.wikidata.org/wiki/Wikidata:Pywikibot_-_Python_3_Tutorial/Setting_up_Shop

4. get wikidata 
  wget https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.bz2 (50 GB) 
  bzip2 -dc latest-all.json.bz2 | grep '"P1883"' >a.decl_refs
  cat a.decl_refs  | sed 's/,$//' |  jq -cr '[.claims.P1883[0].mainsnak.datavalue.value, .sitelinks.ruwiki.title] | @tsv' >claims.1883.txt

5. sparql query in https://query.wikidata.org

SELECT (COUNT(?item) AS ?rc)
WHERE 
{
  ?item wdt:P1883 ?id.
 
} 
SELECT ?item ?itemLabel ?id
WHERE 
{
  ?item wdt:P1883 ?id.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],ru". }
}

6. 
select id, wikipedia from declarations_person where wikipedia is not null and wikipedia <> '' into outfile "/var/lib/mysql-files/decl_wiki_links.txt";

7. Появится ли ссылка на https://ru.wikipedia.org/wiki/%D0%98%D0%B2%D0%B0%D0%BD%D0%BE%D0%B2,_%D0%92%D0%B0%D0%BB%D0%B5%D1%80%D0%B8%D0%B9_%D0%92%D0%B8%D0%BA%D1%82%D0%BE%D1%80%D0%BE%D0%B2%D0%B8%D1%87
в викидате она есть

30 в викидату