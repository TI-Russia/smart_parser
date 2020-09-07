#read   https://tomassetti.me/getting-started-with-antlr-in-csharp/  to know how to install antlr
src_files=`find src -name '*.g4'`
java org.antlr.v4.Tool -visitor -Dlanguage=CSharp  -o generated $src_files
