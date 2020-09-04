parser grammar RealtyParser;
options { tokenVocab=RealtyLexer; }


realty_list : (realty SEMICOLON?)+;

realty : 
		/*Квартира (долевая собственность) 122 кв.м.*/
		/*Квартира, общая долевая собственность ¼ от 44,4 кв.м., РФ */
	     (realty_type COMMA? OPN_BRK? own_type CLS_BRK? COMMA? square COUNTRY?)

		 /*Квартира (комнаты 1,2) 25,7 кв.м Индивидуальная собственность РФ*/
       | (realty_type COMMA? square COMMA? own_type COUNTRY?)

		 /*Земельный участок сельхоз.назначения 1788452000 Долевая собственность 2697/17884 доли РФ*/
       | (realty_type COMMA? REALTY_ID COMMA? own_type COUNTRY?)      

		 /*Участок под ЛПХ (1/2 доли), 14 000,00 м2. Россия*/
       | (realty_type  OPN_BRK? realty_share DOLYA_WORD? CLS_BRK? COMMA? square COMMA?  COUNTRY?)      

	    /*Земельный участок под хозяйственными постройками, 30,00 м2. Россия (аренда)*/
	   | (realty_type  COMMA? square COMMA?  COUNTRY? OPN_BRK? own_type  CLS_BRK? )      
	;

realty_type : REALTY_TYPE;

own_type :    OWN_TYPE
			| (OWN_TYPE DOLYA_WORD? realty_share DOLYA_WORD? OT?);


/*122 кв.м.*/
square : NUMBER  (SQUARE_METER | HECTARE);

/*1/2 доли*/
realty_share : (FRACTION_UNICODE | FRACTION_ASCII);

