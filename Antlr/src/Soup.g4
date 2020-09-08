parser grammar Soup;
import Common;
options { tokenVocab=SoupLexer; }

any_realty_item_list : any_realty_item+;

any_realty_item: 
              country
            | square
            | realty_type
            | own_type
            | INT
            | FLOATING
            | COMMA
   ;
