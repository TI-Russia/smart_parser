parser grammar OwnTypeList;

options { tokenVocab=StrictLexer; }

own_type_list : own_type+;

own_type : (OWN_TYPE COMMA?);


