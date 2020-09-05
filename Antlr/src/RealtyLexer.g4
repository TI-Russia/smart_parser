lexer grammar RealtyLexer;
import  RealtyChars, RealtyOwntype, RealtyCountry, RealtyType;

SQUARE_METER : 'кв.м' | 'кв.м.' | 'м2.' | 'м2';
HECTARE	 : 'га';
OT: 'от';

/* 14 000  14 001,24 */ 
fragment NUMBER_WITH_SPACES : ( [1-9][0-9]?[0-9]? ' ' [0-9][0-9+][0-9] ([.,][0-9][0-9]?[0-9]?)? );

/* short number < 100000 like 1.23, 99999.999 */
fragment NUMBER_WITHOUT_SPACES : [1-9][0-9]?[0-9]?[0-9]?[0-9]?([.,][0-9][0-9]?[0-9]?)?;


NUMBER : NUMBER_WITHOUT_SPACES | NUMBER_WITH_SPACES;

/* long number */
REALTY_ID : [0-9][0-9][0-9][0-9][0-9][0-9][0-9]+;

/*2697/17884 доли*/
FRACTION_ASCII : [1-9][0-9]*[/][1-9][0-9]*;
DOLYA_WORD : 'доли' | 'доля';






