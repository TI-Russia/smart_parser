0. insert into /etc/environment or into ~/.profile
export DECLARATOR_CONV_URL=disclosures.ru:8091
export ASPOSE_LIC=~/lic.bin
export PYTHONPATH=$PYTHONPATH:~/smart_parser/tools


1. Read and follow tools/INSTALL.txt

2. Go to tools/DeclDocRecognizer run tests

3. Return to tools /robots/dlrobot
   
4. download https://github.com/mozilla/geckodriver/releases/tag/v0.26.0 (linux or windows);
   copy geckodriver to  PATH (to ~/.local/bin ?)
   install Firefox

5.  Run tests for dlrobot
     cd test
     bash run_tests.sh



