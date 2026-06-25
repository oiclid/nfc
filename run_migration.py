import sqlite3
import importlib.util

conn = sqlite3.connect('data/nfc_cooperative.db')
conn.row_factory = sqlite3.Row

spec   = importlib.util.spec_from_file_location('m', 'migrations/0007_mark_defaulted_loans.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.up(conn)

conn.execute("INSERT INTO migrations (name) VALUES ('0007_mark_defaulted_loans')")
conn.commit()

print()
print('Loan status summary:')
for r in conn.execute('''
    SELECT status, COUNT(*) as loans,
           ROUND(SUM(principal_amount),2) as principal
    FROM loans GROUP BY status ORDER BY loans DESC
''').fetchall():
    print(dict(r))

conn.close()