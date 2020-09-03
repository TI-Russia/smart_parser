parser grammar RealtyParser;
options { tokenVocab=RealtyLexer; }

/*Квартира (долевая собственность) 122 кв.м.*/

realty_list : realty+;
realty : REALTY_TYPE SPC OWN_TYPE SPC square (SPC SEMICOLON)?;
square : NUMBER SPC SQUARE_METER;
