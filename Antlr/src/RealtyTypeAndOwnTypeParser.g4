/* парсим записи о недвижимости (все в одной строке), без деления по колонкам */

parser grammar RealtyTypeAndOwnTypeParser;
import  RealtyCommonParser;

options { tokenVocab=RealtyLexer; }


realty_list : (HYPHEN? realty SEMICOLON?)+;

realty : 
		/*Квартира (долевая собственность)*/
		/*Квартира, общая долевая собственность  */
	     (realty_type COMMA? OPN_BRK? own_type? CLS_BRK?)

		 /*Участок под ЛПХ (1/2 доли)*/
       | (realty_type  OPN_BRK? realty_share DOLYA_WORD? CLS_BRK?)      


	;

realty_type : REALTY_TYPE;

