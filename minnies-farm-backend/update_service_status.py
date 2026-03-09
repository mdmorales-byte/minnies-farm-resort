"""
Database migration script to update service_avails status enum
Adds 'completed' status to the existing enum
"""

from extensions import db
from app import create_app
import mysql.connector

def update_service_status_enum():
    """Update the service_avails table to include 'completed' status"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get database connection details from app config
            db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
            
            # Parse MySQL connection details
            import re
            match = re.match(r'mysql\+pymysql://(.+?):(.+?)@(.+?):(\d+?)/(.+)', db_uri)
            if match:
                user, password, host, port, database = match.groups()
                
                # Connect directly to MySQL
                conn = mysql.connector.connect(
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                    port=int(port)
                )
                
                cursor = conn.cursor()
                
                # Update the enum column
                alter_query = """
                ALTER TABLE service_avails 
                MODIFY COLUMN status ENUM('pending', 'confirmed', 'cancelled', 'completed') 
                DEFAULT 'confirmed'
                """
                
                cursor.execute(alter_query)
                conn.commit()
                
                print("✅ Successfully updated service_avails status enum to include 'completed'")
                print("✅ The 'Complete' button should now work properly!")
                
                cursor.close()
                conn.close()
                
            else:
                print("❌ Could not parse database URI")
                
        except Exception as e:
            print(f"❌ Error updating database: {e}")
            print("\n💡 Alternative: Run this SQL manually:")
            print("ALTER TABLE service_avails MODIFY COLUMN status ENUM('pending', 'confirmed', 'cancelled', 'completed') DEFAULT 'confirmed';")

if __name__ == "__main__":
    update_service_status_enum()
