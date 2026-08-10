import os
import json
import sqlite3

cxn = sqlite3.connect("dataset.sqlite3.db");
cxn_cursor = cxn.cursor()

cxn_cursor.execute("CREATE TABLE IF NOT EXISTS records (name TEXT PRIMARY KEY, fps INTEGER, ani_data BLOB)", [])

ani_dir = "converted_json"

# store
for filename in os.listdir(ani_dir):
    if filename.endswith(".json"):
        name = filename.rsplit(".", 1)[0].lower().strip()
        full_filepath = os.path.join(ani_dir,filename)
        file = open(full_filepath, "rb")
        data = json.loads(file.read())
        fps = len(data)
        _ = file.seek(0)
        cxn_cursor.execute ("INSERT OR REPLACE INTO records VALUES (?,?,?)", [name, fps, file.read()])
        file.close()

cxn.commit()

# build a fast index
cxn_cursor.execute("ANALYZE", [])

# compress and defrag
cxn_cursor.execute("VACUUM", [])

cxn.close()
