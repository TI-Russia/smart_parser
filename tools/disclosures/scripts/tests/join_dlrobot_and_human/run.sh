python ../../copy_dlrobot_documents_to_one_folder.py --input-glob  processed_projects --output-folder domains
python ../../join_human_and_dlrobot.py --dlrobot-folder domains --human-json human_files.json --old-dlrobot-human-json old/dlrobot_human.json --output-json dlrobot_human.json
