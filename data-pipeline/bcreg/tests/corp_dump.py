
import psycopg2
import logging
import json
import csv

LOGGER = logging.getLogger(__name__)

db = {
    'host': 'localhost',
    'port': '5454',
    'database': 'bc_reg_db',
    'user': 'USER_rh5o',
    'password': 'W3cCW_MzHEtncf6W',
}

sql = """
    select corp_num, corp_state, credential_type_cd, credential_json, entry_date
    from credential_log
    where credential_type_cd = 'REG'
    order by entry_date desc
"""

conn = None
cur = None
corps = {}
corp_types = {}
max_per_type = 100
i = 0
try:
    with open('orgbook_corp_export.csv', 'w', newline='') as csvfile:
        fieldnames = ['corp_num', 'corp_type', 'corp_state', 'corp_name', 'corp_name_assumed', 'effective_date']
        csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csvwriter.writeheader()

        print("Connecting ...")
        conn = psycopg2.connect(**db)

        cur = conn.cursor()
        print("Running query ...")
        cur.execute(sql)
        print("Writing csv file ...")
        row = cur.fetchone()
        while row is not None:
            i = i + 1
            corp_info = {
                'corp_num':row[0],
                'corp_state':row[1], 
                'credential_type_cd':row[2],
                'credential_json':row[3],
                'entry_date':row[4],
            }
            if corp_info["corp_num"] not in corps:
                if corp_info["credential_json"]["entity_type"] not in corp_types:
                    corp_types[corp_info["credential_json"]["entity_type"]] = 0
                corp_types[corp_info["credential_json"]["entity_type"]] = corp_types[corp_info["credential_json"]["entity_type"]] + 1
                if max_per_type >= corp_types[corp_info["credential_json"]["entity_type"]]:
                    corps[corp_info["corp_num"]] = corp_info
                    corp_output = {
                        'corp_num': corp_info["credential_json"]["registration_id"],
                        'corp_type': corp_info["credential_json"]["entity_type"],
                        'corp_state': corp_info["credential_json"]["entity_status"] if "entity_status" in corp_info["credential_json"] else "",
                        'corp_name': corp_info["credential_json"]["entity_name"] if "entity_name" in corp_info["credential_json"] else "",
                        'corp_name_assumed': corp_info["credential_json"]["entity_name_assumed"] if "entity_name_assumed" in corp_info["credential_json"] else "",
                        'effective_date': corp_info["credential_json"]["effective_date"] if "effective_date" in corp_info["credential_json"] else "",
                    }
                    csvwriter.writerow(corp_output)
            row = cur.fetchone()
        cur.close()
        cur = None

except (Exception) as error:
    print(error)
    raise

finally:
    if cur is not None:
        cur.close()
    cur = None
    if conn is not None:
        conn.close()
    conn = None
    print("Done.")

