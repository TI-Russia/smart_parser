lexer grammar RealtyLexer;
import  RealtyOwntype, RealtyCountry, RealtyType;


SEMICOLON : ';';
COMMA : ',';
OPN_BRK : '(';
CLS_BRK : ')';
SPC : (' ')+ -> skip;

SQUARE_METER : 'кв.м' | 'кв.м.';
OT: 'от';
NUMBER : [0-9+]+([.,][0-9+]+)?;
FRACTION_UNICODE : '¼' | '½' | '¾' | '⅐' | '⅑' | '⅒' | '⅓' | '⅔' | '⅕' | '⅖' | '⅗' | '⅘' | '⅙' | '⅚' | '⅛' | '⅜' | '⅝' | '⅞';

FRACTION_ASCII : [1-9][/][1-9][0-9]?;
SHARE : 'доли' | 'доля';




