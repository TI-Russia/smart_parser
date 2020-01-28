set SMART_PARSER=..\..\src\bin\Debug\netcoreapp3.1\smart_parser.exe

# %SMART_PARSER% -adapter aspose -license %ASPOSE_LIC% %1
%SMART_PARSER% -adapter prod -v debug %1
