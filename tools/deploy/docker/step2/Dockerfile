FROM disclosures

#1 test smart_parser
RUN dotnet test -c Release ~/smart_parser

#2 test Office2Txt
RUN dotnet test -c Release ~/smart_parser/tools/Office2Txt

#3 test crawler
RUN cd $HOME/smart_parser/tools/dlrobot/robot && python3 -m unittest -v -f

#4 test crawler manager (=dlrobot_central)
RUN cd $HOME/smart_parser/tools/dlrobot/central && python3 -m unittest -v -f

CMD ["/bin/bash"]
