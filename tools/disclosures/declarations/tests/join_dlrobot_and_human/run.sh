[ ! -d domains ] || rm -rf domains
[ ! -f dlrobot_human.json ] || rm -rf dlrobot_human.json
python ../../copy_dlrobot_documents_to_one_folder.py --input-glob  processed_projects --output-folder domains --use-pseudo-tmp
python ../../join_human_and_dlrobot.py --dlrobot-folder domains --human-json human_files.json --old-dlrobot-human-json old/dlrobot_human.json --output-json dlrobot_human.json
git diff dlrobot_human.json
if [ $?  != 0 ]; then
  echo "test failed"
else
  echo "test succeeded"
fi