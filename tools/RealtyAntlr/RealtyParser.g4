parser grammar RealtyParser;
options { tokenVocab=RealtyLexer; }


realty_list : realty+;

/*Квартира (долевая собственность) 122 кв.м.*/
realty : REALTY_TYPE  OPN_BRK? OWN_TYPE CLS_BRK? square SEMICOLON?;

/*122 кв.м.*/
square : NUMBER  SQUARE_METER;
