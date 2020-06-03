for test_folder in ping check_contain conv_winword conv_ocr bad_and_good complicated_pdf rebuild script_convert_pdf must_be_ocred stalled_files
do
  echo -n "test $test_folder -> "
  cd $test_folder
  [ ! -f test_log.out ] || rm test_log.out
  bash -x run.sh >test_log.out 2>&1
  if [ $? -eq 0 ]; then
     echo "success"
  else
     echo "failed"
     exit 1
  fi
  cd - >/dev/null
done
