#read   https://tomassetti.me/getting-started-with-antlr-in-csharp/  to know how to install antlr

java org.antlr.v4.Tool -visitor -Dlanguage=CSharp  -o generated src/RealtyLexer.g4 src/RealtyAllParser.g4
