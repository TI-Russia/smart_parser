# this script is obsolete, should be rewritten using DECLARATOR conversion server

# cracked pdf files for winword conversion 
mkdir pdf.winword

# cracked pdf files for ocr
mkdir pdf.ocr

# 2. crack pdf and distribute pdf between winword and ocr
python3 copy_new.py --input-glob-pattern 'out.documentfile/*.pdf' --old-json ~/media/converted/converted_file_storage.json  --dest-folder pdf  --dest-folder-for-ocr pdf.ocr --dest-folder-for-winword pdf.winword

# 3. copy pdf.winword  and pdf.ocr files to windows (files in folder 'pdf' can be with drm, keep them but do not use them for conversion)

# 4. run_portion.sh on winwow
                             
# 5. process pdf.ocr with Abbyy Hot Folder (Windows Gui)

# 6. copy all docx files to folder "pdf"

# 7. copy folder "pdf" to ~/media/converted/files
python copy_ready.py --input-glob-pattern './pdf/*.pdf'  --dest-folder ~/media/converted/files


# 8. delete files 
rm pdf/*
rm pdf.winword/*
rm pdf.ocr

# 9. goto  ~/media/converted and rebuild conversion json db
cd ~/media/converted
if [[ -f converted_file_storage.json ]]; then
    cp converted_file_storage.json converted_file_storage.json.bak
fi
python $SCRIPT_FOLDER/create_json.py  --input-glob-pattern './files/*.docx' --output-json converted_file_storage.json
cd -
