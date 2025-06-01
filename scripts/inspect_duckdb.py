# scripts/inspect_duckdb.py

import os
import duckdb

# Path to your DuckDB file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "duckdb_database", "dwpikp.duckdb")

print("▶ Opening DuckDB at:", DB_PATH)
con = duckdb.connect(database=DB_PATH, read_only=True)

# 1) Show tables
print("\n=== SHOW TABLES ===")
tables = con.execute("SHOW TABLES;").fetchall()
for t in tables:
    print("  •", t[0])

# 2) Show a few rows from fact_with_dim
print("\n=== SAMPLE ROWS FROM fact_with_dim ===")
result = con.execute("SELECT * FROM fact_with_dim LIMIT 5;").fetchall()

# Extract column names from con.description; each entry is a tuple whose first element is the column name
colnames = [col_info[0] for col_info in con.description]
print("Columns:", colnames)

# Print each row (tuple)
for row in result:
    print(row)

con.close()
