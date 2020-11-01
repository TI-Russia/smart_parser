#read   https://tomassetti.me/getting-started-with-antlr-in-csharp/  to know how to install antlr
antlr4='java -jar C:\Javalib\antlr-4.8-complete.jar -visitor -Dlanguage=CSharp -o generated'
rm generated/*
$antlr4 src/SoupLexer.g4
$antlr4 src/Soup.g4
$antlr4 src/StrictLexer.g4
$antlr4 src/Strict.g4
$antlr4 src/SquareList.g4
$antlr4 src/CountryList.g4
$antlr4 src/RealtyTypeAndOwnType.g4
$antlr4 src/OwnTypeList.g4
$antlr4 src/RealtyTypeList.g4


