0. insert into /etc/environment or into ~/.profile
export DECLARATOR_CONV_URL=192.168.100.152:8091
export ASPOSE_LIC=~/lic.bin
export PYTHONPATH=$PYTHONPATH:~/smart_parser/tools


1. Read and follow tools/INSTALL.txt to install python packages

2. Go to tools/DeclDocRecognizer and read readme.txt, run tests

3. Return to tools /robots/dlrobot
   
4. download https://github.com/mozilla/geckodriver/releases/tag/v0.26.0 (linux or windows);
   copy geckodriver to  PATH (to ~/.local/bin ?)
   install Firefox

5.  install dotnet according  https://docs.microsoft.com/ru-ru/dotnet/core/install/linux-package-manager-ubuntu-1904
    run dotnet build -c Release ~/smart_parser/src
    run dotnet test -c Release ~/smart_parser/src

6.  Run tests for dlrobot
     cd test
     bash run_tests.sh



