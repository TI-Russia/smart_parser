lexer grammar SquareLexer;

SQUARE_METER : 'кв.м' | 'кв.м.' | 'м2.' | 'м2';
HECTARE	 : 'га';
fragment NUMBER_WITH_SPACES : ( [1-9][0-9]?[0-9]? [ \u00A0] [0-9][0-9+][0-9] ([.,][0-9][0-9]?[0-9]?)? );

/* short number < 100000 like 1.23, 99999.999 */
fragment NUMBER_WITHOUT_SPACES : [1-9][0-9]?[0-9]?[0-9]?[0-9]?([.,][0-9][0-9]?[0-9]?)?;


NUMBER : NUMBER_WITHOUT_SPACES | NUMBER_WITH_SPACES;
