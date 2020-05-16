PROCESSED_FOLDER=$1
project_file=$2
basename_project_file=`basename $project_file`
folder=${basename_project_file%.txt} 
date
echo 'process $project_file'
mkdir $folder
cd $folder
cp $project_file .
python3 /home/sokirko/smart_parser/tools/robots/dlrobot/dlrobot.py --project  $basename_project_file
rm -rf cached
rm -rf geckodriver.log
exit_code=0
if [ ! -f $basename_project_file.clicks.stats ]; then
    echo "cannot find clicks.stats file, dlrobot.py failed, delete result folder "
    rm -rf result
    exit_code=1
fi
cd -
output_folder=$PROCESSED_FOLDER/$folder
if [ -d $output_folder ]; then
    seconds=`date "+%s"`
    output_folder=$output_folder.$seconds
fi
cp -r --no-preserve=mode,ownership $folder $output_folder
rm -rf $folder
exit $exit_code

