/* парсим списки типов недвижимости*/

parser grammar RealtyTypeListParser;

options { tokenVocab=RealtyLexer; }

realty_type_list : realty_type+;

realty_type : (REALTY_TYPE COMMA?);


