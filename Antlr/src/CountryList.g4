/* парсим списки стран */

parser grammar CountryList;

options { tokenVocab=StrictLexer; }

countries : country+;

country : (COUNTRY COMMA?);


