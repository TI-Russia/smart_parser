/* No numbers with spaces */
parser grammar SquareListParser;
import  CommonForParsers;
options { tokenVocab=StrictLexer; }

bareSquares : bareScore+;
bareScore: square_value_without_spaces;



