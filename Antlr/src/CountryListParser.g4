/* парсим списки стран */

parser grammar CountryListParser;

options { tokenVocab=RealtyLexer; }

countries : country+;

country : (COUNTRY COMMA?);


