import os
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST", os.getenv("DB_HOST", "localhost")),
        user=os.getenv("MYSQLUSER", os.getenv("DB_USER", "root")),
        password=os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", "")),
        database=os.getenv("MYSQLDATABASE", os.getenv("DB_NAME", "eventify_db")),
        port=int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", "3306")))
    )
