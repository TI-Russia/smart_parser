parser grammar RealtyParser;
options { tokenVocab=RealtyLexer; }

/*Квартира (долевая собственность) 122 кв.м.*/

realty_list : realty+;
realty : REALTY_TYPE  OWN_TYPE square ( SEMICOLON)?;
square : NUMBER  SQUARE_METER;
