
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'root1234'),
            database=os.getenv('DB_NAME', 'minnies_farm_db'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = conn.cursor()
        
        print("Checking services table...")
        cursor.execute("DESCRIBE services")
        columns = [col[0] for col in cursor.fetchall()]
        
        if 'stock_quantity' not in columns:
            print("Adding stock_quantity column to services table...")
            cursor.execute("ALTER TABLE services ADD COLUMN stock_quantity INT DEFAULT -1")
            conn.commit()
            print("✅ Column added successfully.")
        else:
            print("✅ stock_quantity column already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_db()
