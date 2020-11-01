lexer grammar BaseLexer;

SEMICOLON : ';';
COMMA : ',';
OPN_BRK : '(';
CLS_BRK : ')';
FRACTION_UNICODE : '¼' | '½' | '¾' | '⅐' | '⅑' | '⅒' | '⅓' | '⅔' | '⅕' | '⅖' | '⅗' | '⅘' | '⅙' | '⅚' | '⅛' | '⅜' | '⅝' | '⅞';
HYPHEN : '-';
FLOATING : [0-9]+[.,][0-9]+;
BULLET: [1-9][.];
INT : [0-9]+;
OT: 'от';
WEB_LINK : 'http' 's'? '://' [a-z0-9./]+;
SQUARE_METER : 'кв.м' | 'кв.м.' | 'м2.' | 'м2';
HECTARE	 : 'га';

/*2697/17884 доли*/
FRACTION_ASCII : INT[/]INT;

DOLYA_WORD : 'доли' | 'доля';

SPC : (' ')+ -> skip;
