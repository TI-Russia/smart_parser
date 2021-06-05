
Читал:

  https://tomassetti.me/getting-started-with-antlr-in-csharp/

  https://github.com/joaoBordalo/feup-COMP/raw/master/The%20Definitive%20ANTLR%204%20Reference.pdf

1. install nuget package Antlr4BuildTasks
2. install nuget package Antlr4.Runtime.Standard
3. Файлы из Antlr должны генерироваться в каталог generated командой (rebuild  solution). Команда "Build solution" не строит их.
В командной строке надо добавлять --no-incremental
		dotnet build -c Release --no-incremental ~/smart_parser/src


3. Если java (jdk) уже установлена,  нужно  скачать jar antlr-4.8-complete.jar со страницы 
разработчика Antlr (https://www.antlr.org/download.html ). Потом указать в BuildAntlr.csproj для каждого файл *.g4 
путь до java (jdk) и до скаченного antlr-??-complete.jar, примерно так:
        <Antlr4 Include="src\BaseLexer.g4">
          <JavaExe>C:\Program Files\Java\jdk-14\bin\java.exe</JavaExe>
          <AntlrRuntime>C:\Javalib\antlr-4.8-complete.jar</AntlrRuntime>
          <AntOutDir>generated</AntOutDir>
        </Antlr4>

4. можно попробовать сгенерировать файлы с помощью generate_csharp_from_antlr.sh, но тогда jdk должен быть установлена
и команда java должна быть в пути.
