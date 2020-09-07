parser grammar CommonForParsers;

own_type :    OWN_TYPE
			| (OWN_TYPE DOLYA_WORD? COMMA? realty_share DOLYA_WORD? OT?);


/*1/2 доли*/
realty_share : (FRACTION_UNICODE | FRACTION_ASCII);


/*122 кв.м.*/
square : NUMBER  (SQUARE_METER | HECTARE);


realty_type : REALTY_TYPE;

country : COUNTRY;