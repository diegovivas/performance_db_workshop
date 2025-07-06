import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def create_table():
    conn = None
    cursor = None
    try:
        # Database connection parameters
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", 5432),
            user=os.getenv("POSTGRES_USER", "testuser"),
            password=os.getenv("POSTGRES_PASSWORD", "testpass"),
            database=os.getenv("POSTGRES_DB", "testdb")
        )
        
        cursor = conn.cursor()
        
        # Create ecommerce_orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ecommerce_orders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                order_number VARCHAR(20) UNIQUE NOT NULL,
                customer_email VARCHAR(255) NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                payment_method VARCHAR(50),
                shipping_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                items_count INTEGER DEFAULT 1,
                is_express_shipping BOOLEAN DEFAULT FALSE,
                discount_code VARCHAR(50),
                tax_amount DECIMAL(10,2) DEFAULT 0.00
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ecommerce_orders_user_id 
            ON ecommerce_orders(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ecommerce_orders_status 
            ON ecommerce_orders(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ecommerce_orders_created_at 
            ON ecommerce_orders(created_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ecommerce_orders_customer_email 
            ON ecommerce_orders(customer_email)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ecommerce_orders_order_number 
            ON ecommerce_orders(order_number)
        """)
        
        conn.commit()
        print("PostgreSQL table 'ecommerce_orders' and indexes created successfully.")
        
    except Exception as e:
        print(f"Error creating PostgreSQL table: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    create_table() 