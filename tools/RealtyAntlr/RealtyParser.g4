parser grammar RealtyParser;
options { tokenVocab=RealtyLexer; }


realty_list : realty+;


realty : 
		/*Квартира (долевая собственность) 122 кв.м.*/
	   (REALTY_TYPE  OPN_BRK? OWN_TYPE CLS_BRK? square COUNTRY? SEMICOLON?)

		/*Квартира, общая долевая собственность ¼ от 44,4 кв.м., РФ */
	 | (REALTY_TYPE COMMA OWN_TYPE realty_share OT square COMMA COUNTRY? SEMICOLON?)
	;


/*122 кв.м.*/
square : NUMBER  SQUARE_METER;

realty_share : (FRACTION_UNICODE | FRACTION_ASCII);
