import pymysql

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='Admin@123',
    database='comm_platform',
    charset='utf8mb4'
)

cursor = conn.cursor()
cursor.execute("SHOW TABLES LIKE 'm03_%'")
tables = [row[0] for row in cursor.fetchall()]
print("M03 tables:", tables)

cursor.execute("SELECT id, name, category FROM m03_parametric_template")
templates = cursor.fetchall()
print("\nTemplates:")
for t in templates:
    print(f"  ID: {t[0]}, Name: {t[1]}, Category: {t[2]}")

conn.close()
