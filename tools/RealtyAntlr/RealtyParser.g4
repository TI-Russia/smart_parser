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
	;

realty_type : REALTY_TYPE realty_addition?;
own_type :    OWN_TYPE
			| (OWN_TYPE SHARE? realty_share SHARE? OT?);


/*для "(комнаты 1,2)" в примере Квартира (комнаты 1,2) 25,7 кв.м Индивидуальная собственность РФ*/
realty_addition : OPN_BRK REALTY_PARTS NUMBER (COMMA NUMBER)*  CLS_BRK;

/*122 кв.м.*/
square : NUMBER  (SQUARE_METER | HECTARE);

/*1/2 доли*/
realty_share : (FRACTION_UNICODE | FRACTION_ASCII);

