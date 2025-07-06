import os
import random
import string
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from locust import User, constant, events, tag, task

load_dotenv()

# PostgreSQL connection pool
try:
    postgres_pool = pool.SimpleConnectionPool(
        1, 50,
        user=os.getenv("POSTGRES_USER", "testuser"),
        password=os.getenv("POSTGRES_PASSWORD", "testpass"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", 5432),
        database=os.getenv("POSTGRES_DB", "testdb")
    )
    if postgres_pool:
        print("PostgreSQL connection pool created successfully")
except Exception as e:
    print(f"Error creating PostgreSQL connection pool: {e}")

# Store inserted IDs for update/delete operations
inserted_ids = []

# E-commerce data 
ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]
PAYMENT_METHODS = ["credit_card", "paypal", "bank_transfer", "apple_pay", "google_pay"]
DISCOUNT_CODES = [None, "SAVE10", "WELCOME20", "BLACKFRIDAY", "SUMMER25", "FREESHIP"]
CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", 
          "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville"]


class PostgresUser(User):
    wait_time = constant(1)  # 1 second wait between tasks

    def on_start(self):
        self.conn = postgres_pool.getconn()
        self.cursor = self.conn.cursor()

    def on_stop(self):
        self.cursor.close()
        postgres_pool.putconn(self.conn)

    @task(4)  # Higher weight for inserts
    @tag("insert")
    def insert_ecommerce_order(self):
        """Insert data (CREATE operation)"""
        record_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        # Generate unique order number using UUID to avoid duplicates
        order_number = f"ORD-{str(uuid.uuid4())[:8].upper()}"
        
        data = {
            "id": record_id,
            "user_id": user_id,
            "order_number": order_number,
            "customer_email": f"customer{random.randint(1, 10000)}@example.com",
            "total_amount": Decimal(str(round(random.uniform(10.0, 1000.0), 2))),
            "status": random.choice(ORDER_STATUSES),
            "payment_method": random.choice(PAYMENT_METHODS),
            "shipping_address": f"{random.randint(100, 9999)} {random.choice(['Main St', 'Oak Ave', 'Park Blvd', 'First St'])}, {random.choice(CITIES)}",
            "created_at": datetime.now() - timedelta(days=random.randint(0, 365)),
            "updated_at": datetime.now(),
            "items_count": random.randint(1, 10),
            "is_express_shipping": random.choice([True, False]),
            "discount_code": random.choice(DISCOUNT_CODES),
            "tax_amount": Decimal(str(round(random.uniform(0.0, 50.0), 2)))
        }

        insert_query = """
        INSERT INTO ecommerce_orders (
            id, user_id, order_number, customer_email, total_amount, status,
            payment_method, shipping_address, created_at, updated_at, items_count,
            is_express_shipping, discount_code, tax_amount
        ) VALUES (
            %(id)s, %(user_id)s, %(order_number)s, %(customer_email)s, %(total_amount)s, %(status)s,
            %(payment_method)s, %(shipping_address)s, %(created_at)s, %(updated_at)s, %(items_count)s,
            %(is_express_shipping)s, %(discount_code)s, %(tax_amount)s
        )
        """
        try:
            self.cursor.execute(insert_query, data)
            self.conn.commit()
            # Store ID for later update/delete operations
            if len(inserted_ids) < 1000:  # Limit stored IDs
                inserted_ids.append(record_id)
        except Exception as e:
            self.conn.rollback()
            print(f"Error inserting data: {e}")

    @task(3)  # Read operations
    @tag("read")
    def read_ecommerce_orders(self):
        """Read data (READ operation)"""
        try:
            # Random query patterns
            query_type = random.choice(['by_status', 'by_user', 'by_email', 'by_date_range', 'by_id', 'recent_orders'])
            
            if query_type == 'by_status':
                status = random.choice(ORDER_STATUSES)
                query = """
                SELECT * FROM ecommerce_orders 
                WHERE status = %s 
                ORDER BY created_at DESC
                LIMIT 100
                """
                self.cursor.execute(query, (status,))
                
            elif query_type == 'by_user' and inserted_ids:
                # Try to find orders for a user we know exists
                query = """
                SELECT * FROM ecommerce_orders 
                WHERE user_id = (SELECT user_id FROM ecommerce_orders LIMIT 1)
                LIMIT 50
                """
                self.cursor.execute(query)
                
            elif query_type == 'by_email':
                email_prefix = f"customer{random.randint(1, 1000)}"
                query = """
                SELECT * FROM ecommerce_orders 
                WHERE customer_email LIKE %s 
                LIMIT 50
                """
                self.cursor.execute(query, (f"{email_prefix}%",))
                
            elif query_type == 'by_date_range':
                start_date = datetime.now() - timedelta(days=30)
                end_date = datetime.now()
                query = """
                SELECT * FROM ecommerce_orders 
                WHERE created_at >= %s AND created_at <= %s 
                ORDER BY created_at DESC
                LIMIT 100
                """
                self.cursor.execute(query, (start_date, end_date))
                
            elif query_type == 'by_id' and inserted_ids:
                random_id = random.choice(inserted_ids)
                query = "SELECT * FROM ecommerce_orders WHERE id = %s"
                self.cursor.execute(query, (random_id,))
                
            else:  # recent_orders
                query = """
                SELECT * FROM ecommerce_orders 
                ORDER BY created_at DESC 
                LIMIT 50
                """
                self.cursor.execute(query)
            
            rows = self.cursor.fetchall()
            
        except Exception as e:
            print(f"Error reading data: {e}")

    @task(2)  # Update operations
    @tag("update")
    def update_ecommerce_order(self):
        """Update data (UPDATE operation)"""
        if not inserted_ids:
            return
            
        try:
            random_id = random.choice(inserted_ids)
            new_status = random.choice(ORDER_STATUSES)
            new_total = Decimal(str(round(random.uniform(10.0, 1000.0), 2)))
            
            update_query = """
            UPDATE ecommerce_orders 
            SET status = %s, total_amount = %s, updated_at = %s
            WHERE id = %s
            """
            
            self.cursor.execute(update_query, (new_status, new_total, datetime.now(), random_id))
            self.conn.commit()
            
                
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating data: {e}")

    @task(1)  # Lower weight for deletes
    @tag("delete")
    def delete_ecommerce_order(self):
        """Delete data (DELETE operation)"""
        if not inserted_ids:
            return
            
        try:
            # Remove a random ID from our list and delete it
            if inserted_ids:
                random_id = inserted_ids.pop(random.randint(0, len(inserted_ids) - 1))
                
                delete_query = "DELETE FROM ecommerce_orders WHERE id = %s"
                self.cursor.execute(delete_query, (random_id,))
                self.conn.commit()
                
                
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting data: {e}")

    def _random_string(self, length):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


