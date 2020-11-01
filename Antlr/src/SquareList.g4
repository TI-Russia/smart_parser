/* No numbers with spaces */
parser grammar SquareList;
import  Common;
options { tokenVocab=StrictLexer; }

bareSquares : bareScore+;
bareScore: square_value_without_spaces;



