lexer grammar RealtyLexer;


SEMICOLON : ';';
COMMA : ',';
OPN_BRK : '(';
CLS_BRK : ')';
SPC : (' ')+ -> skip;

SQUARE_METER : 'кв.м.';
OT: 'от';
NUMBER : [0-9+]+([.,][0-9+]+)?;
FRACTION_UNICODE : '¼' | '½' | '¾' | '⅐' | '⅑' | '⅒' | '⅓' | '⅔' | '⅕' | '⅖' | '⅗' | '⅘' | '⅙' | '⅚' | '⅛' | '⅜' | '⅝' | '⅞';
FRACTION_ASCII : [1-9]/[1-9][0-9]?;

REALTY_TYPE :   'квартира'
              | 'земельный участок'
              | 'жилой дом'
              ;
              
OWN_TYPE :   'долевая собственность'
           | 'индивидуальная собственность'
           | 'индивидуальная'
           | 'в пользовании'
           | 'общая долевая собственность'
           ;

COUNTRY : 'россия'
        | 'рф';


