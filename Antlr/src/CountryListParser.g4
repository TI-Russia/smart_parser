/* парсим списки стран */

parser grammar CountryListParser;

options { tokenVocab=StrictLexer; }

countries : country+;

country : (COUNTRY COMMA?);


