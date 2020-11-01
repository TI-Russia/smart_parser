parser grammar Common;


/* long number */
realty_id : INT 
	{$INT.int > 6000000}?;


square_value_without_spaces : FLOATING | INT  
	{$INT.int < 6000000}?
;

square_value_with_spaces : INT INT? (FLOATING | INT)
	{$INT.int < 1000}?
;

square_value :   square_value_without_spaces
               | square_value_with_spaces;


own_type :    OWN_TYPE
			| (OWN_TYPE DOLYA_WORD? COMMA? realty_share DOLYA_WORD? OT?);


/*1/2 доли*/
realty_share : (FRACTION_UNICODE | FRACTION_ASCII);


/*122 кв.м.*/
square : square_value  (SQUARE_METER | HECTARE);


realty_type : REALTY_TYPE;

country : COUNTRY;