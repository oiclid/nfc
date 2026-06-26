import sqlite3

conn = sqlite3.connect('data/nfc_cooperative.db')
conn.execute("DELETE FROM migrations WHERE name='0005_rename_fees.py'")
conn.commit()
conn.close()
print('Done')