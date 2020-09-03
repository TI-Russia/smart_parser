lexer grammar RealtyLexer;


FLOATING_POINT: '.';
SEMICOLON : ';';
NUMBER : [0-9+]+(FLOATING_POINT[0-9+]+)?;
SPC : (' ')+ -> skip;
OPN_BRK : '(';
CLS_BRK : ')';

SQUARE_METER : 'кв.м.';

REALTY_TYPE :   'квартира'
              | 'земельный участок'
              | 'жилой дом'
              ;
              
OWN_TYPE :   'долевая собственность'
           | 'индивидуальная собственность'
           | 'индивидуальная'
           ;



