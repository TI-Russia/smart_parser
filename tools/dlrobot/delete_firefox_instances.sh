echo "we are gonna to kill all firefox instances!"
os_name=`python3 -c $'import os\nprint (os.name)' | tr -d '\r' `
if [ $os_name == "posix" ]; then
  pkill firefox
else
  taskkill /F  /IM firefox.exe
fi
