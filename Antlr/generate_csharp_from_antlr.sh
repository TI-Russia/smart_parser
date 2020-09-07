#read   https://tomassetti.me/getting-started-with-antlr-in-csharp/  to know how to install antlr
antlr4='java -jar C:\Javalib\antlr-4.8-complete.jar -visitor -Dlanguage=CSharp -o generated'
                                                                               
#src_files=`gfind src -name '*.g4' `
rm generated/*


#java org.antlr.v4.Tool -visitor -Dlanguage=CSharp  -o generated $src_files
$antlr4 src/SoupLexer.g4
$antlr4 src/SoupParser.g4
