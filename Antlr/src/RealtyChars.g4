lexer grammar RealtyLexer;

SEMICOLON : ';';
COMMA : ',';
OPN_BRK : '(';
CLS_BRK : ')';
SPC : (' ')+ -> skip;
FRACTION_UNICODE : '¼' | '½' | '¾' | '⅐' | '⅑' | '⅒' | '⅓' | '⅔' | '⅕' | '⅖' | '⅗' | '⅘' | '⅙' | '⅚' | '⅛' | '⅜' | '⅝' | '⅞';

