/* парсим записи о недвижимости (все в одной строке), без деления по колонкам */

parser grammar RealtyAllParser;

options { tokenVocab=RealtyLexer; }


realty_list : (HYPHEN? realty SEMICOLON?)+;

realty : 
		/*Квартира (долевая собственность) 122 кв.м.*/
		/*Квартира, общая долевая собственность ¼ от 44,4 кв.м., РФ */
		/*Земельный участок Долевая ½ 2164 кв.м */
	     (realty_type COMMA? OPN_BRK? own_type CLS_BRK? COMMA? square COMMA? COUNTRY?)

		 /*Квартира (комнаты 1,2) 25,7 кв.м Индивидуальная собственность РФ*/
       | (realty_type COMMA? square COMMA? own_type COMMA? COUNTRY?)

		 /*Земельный участок сельхоз.назначения 1788452000 Долевая собственность 2697/17884 доли РФ*/
       | (realty_type COMMA? REALTY_ID COMMA? own_type COMMA? COUNTRY?)      

		 /*Участок под ЛПХ (1/2 доли), 14 000,00 м2. Россия*/
       | (realty_type  OPN_BRK? realty_share DOLYA_WORD? CLS_BRK? COMMA? square COMMA?  COUNTRY?)      

	    /*Земельный участок под хозяйственными постройками, 30,00 м2. Россия (аренда)*/
	   | (realty_type  COMMA? square COMMA?  COUNTRY? OPN_BRK? own_type  CLS_BRK? )      

	   /* Земельный участок для ведения с/х, 58 269,00 м2. Россия */
	   | (realty_type  COMMA? square COMMA?  COUNTRY?)      
	;

realty_type : REALTY_TYPE;

own_type :    OWN_TYPE
			| (OWN_TYPE DOLYA_WORD? COMMA? realty_share DOLYA_WORD? OT?);


/*122 кв.м.*/
square : NUMBER  (SQUARE_METER | HECTARE);

/*1/2 доли*/
realty_share : (FRACTION_UNICODE | FRACTION_ASCII);

