# созданеи базы конвертации в старом режиме (уже не работает сейчас)
# нужно удалить этот каталог и все файлы в 2021 году(поскольку даже сейчас нужны на всякий случай)
 


CONVERSION_DB=~/media/converted
JSON_FILE=converted_file_storage.json

# 1. download_all_documents.py downnloads incrementally
python3 ../../robots/robots/join_human_and_dlrobot/download_all_documents.py --table declarations_documentfile --output-folder out.documentfile

#original pdf files
mkdir pdf

# cracked pdf files for winword conversion 
mkdir pdf.winword

# cracked pdf files for ocr
mkdir pdf.ocr

# 2. crack pdf and distribute pdf between winword and ocr
python3 copy_new.py --input-glob-pattern 'out.documentfile/*.pdf' --old-json $CONVERSION_DB/$OLD_JSON  --dest-folder pdf  --dest-folder-for-ocr pdf.ocr --dest-folder-for-winword pdf.winword

# 3. copy pdf.winword  and pdf.ocr files to windows (files in folder 'pdf' can be with drm, keep them but do not use them for conversion)

# 4. run_portion.sh on winwow
                             
# 5. process pdf.ocr with Abbyy Hot Folder (Windows Gui)

# 6. copy all docx files to folder "pdf"

# 7. copy folder "pdf" to ~/media/converted/files
python copy_ready.py --input-glob-pattern './pdf/*.pdf'  --dest-folder $CONVERSION_DB/files

# 8. delete files
rm pdf/*
rm pdf.winword/*
rm pdf.ocr

# 9. goto  ~/media/converted and rebuild conversion json db
SCRIPT_FOLDER=`pwd`
cd $CONVERSION_DB
python $SCRIPT_FOLDER/create_json.py  --input-glob-pattern './files/*.docx' --output-json $JSON_FILE

