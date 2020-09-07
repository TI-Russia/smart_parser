lexer grammar CommonForLexers;

SEMICOLON : ';';
COMMA : ',';
OPN_BRK : '(';
CLS_BRK : ')';
SPC : (' ')+ -> skip;
FRACTION_UNICODE : '¼' | '½' | '¾' | '⅐' | '⅑' | '⅒' | '⅓' | '⅔' | '⅕' | '⅖' | '⅗' | '⅘' | '⅙' | '⅚' | '⅛' | '⅜' | '⅝' | '⅞';
HYPHEN : '-';


OT: 'от';

/* long number */
REALTY_ID : [0-9][0-9][0-9][0-9][0-9][0-9][0-9]+;

/*2697/17884 доли*/
FRACTION_ASCII : [1-9][0-9]*[/][1-9][0-9]*;
DOLYA_WORD : 'доли' | 'доля';
