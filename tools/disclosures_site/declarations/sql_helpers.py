from django.db import connection
import gc
from django.conf import settings
import os


def fetch_cursor_by_chunks(sql_query):
    with connection.cursor() as cursor:
        cursor.execute(sql_query)
        while True:
            results = cursor.fetchmany(10000)
            if not results:
                break
            for x in results:
                yield x
            gc.collect()


def queryset_iterator(queryset, chunksize=1000):
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


def run_sql_script(logger, sql_script_path):
    cmd = "mysql -u {} -p{} -D {} <  {}".format(
        settings.DATABASES['default']['USER'],
        settings.DATABASES['default']['PASSWORD'],
        settings.DATABASES['default']['NAME'],
        sql_script_path
    )

    logger.info(cmd)
    if os.system(cmd) != 0:
        msg = "running mysql script {} failed!".format(sql_script_path)
        logger.error(msg)
        raise Exception(msg)
