FROM ubuntu:20.04

#1 initlialize locales in ubuntu
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

#build Russian locale
RUN apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/* \
	&& localedef -i ru_RU -c -f UTF-8 -A /usr/share/locale/locale.alias ru_RU.UTF-8

# build  English locale
RUN apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/* \
        && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

ENV LANG en_US.UTF-8
ENV HOME /root
ENV TERM xterm
RUN apt-get update && rm -rf /var/lib/apt/lists/*
RUN apt update


#2 main variables
COPY lic.bin $HOME
ENV TOOLS=$HOME/smart_parser/tools
ENV PYTHONPATH=$TOOLS/disclosures_site:$TOOLS
ENV DECLARATOR_CONV_URL=c.disclosures.ru:8091
ENV ASPOSE_LIC=$HOME/lic.bin



#3 install python, curl, git, nano ...
RUN DEBIAN_FRONTEND=noninteractive apt-get install  -y curl p7zip-full unrar libcurl4-openssl-dev libssl-dev libreoffice \
                python3-wheel calibre  catdoc xlsx2csv default-libmysqlclient-dev libgdiplus python3-pip python3.8-dev \
            git  sshfs libcurl4  libxss1 libappindicator1 libindicator7 pdfcrack qpdf abiword wget python3.8-gdbm nano


#4 get sources from github
RUN git clone https://github.com/TI-Russia/smart_parser.git $HOME/smart_parser

#5 install python modules
RUN pip3 install -r ~/smart_parser/tools/requirements.txt

#6  install dotnet (c#)
RUN wget  https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
RUN dpkg -i packages-microsoft-prod.deb
RUN apt-get update
RUN apt-get install -y apt-transport-https
RUN apt-get update
RUN apt-get install -y dotnet-sdk-3.1

#7 compile smart_parser
RUN dotnet build -c Release --no-incremental ~/smart_parser/src
RUN dotnet build -c Release ~/smart_parser/tools/Office2Txt


#8 install google chrome of a specific version
RUN wget -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_93.0.4577.63-1_amd64.deb
RUN apt install -y /tmp/chrome.deb
RUN rm /tmp/chrome.deb

#9 Install chromedriver
RUN rm -rf chromedriver_linux64.zip
RUN wget https://chromedriver.storage.googleapis.com/93.0.4577.15/chromedriver_linux64.zip
RUN rm -rf chromedriver
RUN unzip chromedriver_linux64.zip
RUN mv chromedriver /usr/bin


CMD ["/bin/bash"]
