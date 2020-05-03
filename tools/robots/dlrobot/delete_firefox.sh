echo "we are gonna to kill all firefox instances!"
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    CYGWIN*)    machine=Cygwin;;
    *)          machine="UNKNOWN:${unameOut}"
esac

if [ $machine == "Cygwin" ]; then
  taskkill /F  /IM firefox.exe
else
  pkill firefox
fi
