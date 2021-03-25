
OLD_DB=$1
NEW_DB=$2
MYSQL="mysql -u disclosures -pdisclosures"

if [ -z "$OLD_DB" ]; then
  echo "Usage: bash rename_db.sh <old_db> <new_db>"
  exit 1
fi

if [ -z "$NEW_DB" ]; then
  echo "Usage: bash rename_db.sh <old_db> <new_db>"
  exit 1
fi

function check_db_exist() {
  local db_name=$1
  db_grep=`$MYSQL -NqfsBe "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='$db_name'" 2>&1 |  { grep -v Warning || true; } `
  if [[ ! -z "$db_grep" ]];
  then
    return 1
  else
    return 0
  fi
}

check_db_exist $NEW_DB
if [ $? == 1 ]; then
  echo "target db $NEW_DB already exists, drop it before move"
  exit 1
fi

check_db_exist $OLD_DB
if [ $? == 0 ]; then
  echo "source db $OLD_DB does not exist"
  exit 1
fi

set -e

export DISCLOSURES_DATABASE_NAME=$NEW_DB
python3 $(dirname $0)/../manage.py create_database --settings disclosures.settings.prod --skip-checks --username db_creator --password root

for table in `$MYSQL -u disclosures -pdisclosures -s -N -e "use $OLD_DB;show tables from $OLD_DB;"`;  do
    $MYSQL -s -N -e "use $OLD_DB;rename table $OLD_DB.$table to $NEW_DB.$table;";
done

