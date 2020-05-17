0. положить в /etc/environment
export DECLARATOR_CONV_URL=192.168.100.152:8091
export ASPOSE_LIC=/home/sokirko/lic.bin
export PYTHONPATH=$PYTHONPATH:/home/sokirko/smart_parser/tools

   
1. download https://github.com/mozilla/geckodriver/releases/tag/v0.26.0 (linux or windows)
2. copy geckodriver to  PATH (to ~/.local/bin ?)
3. install Firefox
4.  install dotnet according
 https://docs.microsoft.com/ru-ru/dotnet/core/install/linux-package-manager-ubuntu-1904
5.  dotnet build -c Release ~/smart_parser/src
5.1. sudo apt install  curl
5.2  sudo apt install p7zip-full
5.3. sudo apt install   unrar
5.4  sudo apt install libcurl4-openssl-dev libssl-dev
5.5. install libreoffice

6. pip3 install -r requirements.txt
9. go to ../../DeclDocRecognizer and read readme.txt, run tests
10. 
     cd test
     bash run_tests.sh



