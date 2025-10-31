import psycopg2

DB_CONFIG = {
    "dbname": "satellite_db",
    "user": "postgres",
    "password": "sanjibanipaul",
    "host": "localhost",
    "port": "5432"
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

with open('create_analysis_table.sql', 'r') as f:
    cur.execute(f.read())

conn.commit()
cur.close()
conn.close()