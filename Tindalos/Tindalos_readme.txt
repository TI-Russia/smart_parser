Currently column recognizer can be used by building and running the console app Tindalos.exe.

Building console project Tindalos should be relatively straightforward with any relatively modern version of Visual Studio.
It does not contain any external dependencies besides NuGet packages.

Tindalos.exe accepts directory or file name via a single command line argument.
The app should be able to handle paths containing whitespaces as well as double-quoted paths.

If the app is passed a file name, e.g.:

> tindalos.exe 2010_Sotrudniki_ministerstva.docx

it will scan the Word file and output its column structure into the new text file named "2010_Sotrudniki_ministerstva.txt".

If the app is passed a directory name, e.g.:

> tindalos.exe d:\lab\Transparency\Declarations\min_trans\

it will scan all files in the directory and place info about their column structure into the file named "min_trans.txt".
Additionally, it will recursively scan all the subdirectories in the min_trans directory and place the results into respective text files.
Each additional output file will be named after respective subdirectory (for example, "2014.txt", "2015.txt" and so on).

Column recognizer may encounter difficulties (e.g., a column structure currently beyond its comprehension).
In that case it will dump information about the error into the errors.log file and notify the user via console.

Hope y'all will find it useful


