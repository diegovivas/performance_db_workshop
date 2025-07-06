import os
import random
import string
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from cassandra.cluster import Cluster, DCAwareRoundRobinPolicy
from dotenv import load_dotenv
from locust import User, constant, tag, task

load_dotenv()

# ScyllaDB connection setup
contact_points = os.getenv("CASSANDRA_CONTACT_POINTS", "127.0.0.1").split(",")
cassandra_port = int(os.getenv("CASSANDRA_PORT", 9042))
keyspace = os.getenv("CASSANDRA_KEYSPACE", "ecommerce_keyspace")
local_dc = os.getenv("CASSANDRA_LOCAL_DC", "datacenter1")

cluster = Cluster(
    contact_points,
    port=cassandra_port,
    load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=local_dc),
    protocol_version=4,
    compression=True,
)
session = cluster.connect()

# Create keyspace and table if they don't exist
session.execute(f"""
    CREATE KEYSPACE IF NOT EXISTS {keyspace}
    WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}}
""")
session.set_keyspace(keyspace)

# Store inserted IDs for update/delete operations
inserted_ids = []

# E-commerce data for realistic testing
ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]
PAYMENT_METHODS = ["credit_card", "paypal", "bank_transfer", "apple_pay", "google_pay"]
DISCOUNT_CODES = [None, "SAVE10", "WELCOME20", "BLACKFRIDAY", "SUMMER25", "FREESHIP"]
CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", 
          "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville"]


class ScyllaUser(User):
    wait_time = constant(1)  # 1 second

    @task(4)  # Higher weight for inserts
    @tag("insert")
    def insert_ecommerce_order(self):
        """Insert data (CREATE operation)"""
        start_time = datetime.now()
        record_id = uuid.uuid4()
        user_id = uuid.uuid4()
        # Generate unique order number using UUID to avoid duplicates
        order_number = f"ORD-{str(uuid.uuid4())[:8].upper()}"
        
        try:
            query = """
            INSERT INTO ecommerce_orders (
                id, user_id, order_number, customer_email, total_amount, status,
                payment_method, shipping_address, created_at, updated_at, items_count,
                is_express_shipping, discount_code, tax_amount
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            
            session.execute(query, (
                record_id,
                user_id,
                order_number,
                f"customer{random.randint(1, 10000)}@example.com",
                Decimal(str(round(random.uniform(10.0, 1000.0), 2))),
                random.choice(ORDER_STATUSES),
                random.choice(PAYMENT_METHODS),
                f"{random.randint(100, 9999)} {random.choice(['Main St', 'Oak Ave', 'Park Blvd', 'First St'])}, {random.choice(CITIES)}",
                datetime.now() - timedelta(days=random.randint(0, 365)),
                datetime.now(),
                random.randint(1, 10),
                random.choice([True, False]),
                random.choice(DISCOUNT_CODES),
                Decimal(str(round(random.uniform(0.0, 50.0), 2)))
            ))
            
            # Store ID for later update/delete operations
            if len(inserted_ids) < 1000:  # Limit stored IDs
                inserted_ids.append(record_id)
            
            # Report successful insert metrics to Locust
            self._report("ScyllaDB_INSERT", start_time)
            
        except Exception as e:
            self._report("ScyllaDB_INSERT", start_time, exc=e)
            print(f"Error inserting data: {e}")

    @task(3)  # Read operations
    @tag("read")
    def read_ecommerce_orders(self):
        """Read data (READ operation)"""
        start_time = datetime.now()
        try:
            # Random query patterns
            query_type = random.choice(['by_id', 'by_status', 'random_sample'])
            
            if query_type == 'by_id' and inserted_ids:
                random_id = random.choice(inserted_ids)
                query = "SELECT * FROM ecommerce_orders WHERE id = %s"
                rows = session.execute(query, (random_id,))
                operation_name = "ScyllaDB_READ_BY_ID"
            # elif query_type == 'by_status':
            #     status = random.choice(ORDER_STATUSES)
            #     query = "SELECT * FROM ecommerce_orders WHERE status = %s LIMIT 100 ALLOW FILTERING"
            #     rows = session.execute(query, (status,))
            #     operation_name = "ScyllaDB_READ_BY_STATUS"
            else:  # random_sample
                query = "SELECT * FROM ecommerce_orders LIMIT 50"
                rows = session.execute(query)
                operation_name = "ScyllaDB_READ_SAMPLE"
            
            # Consume the results
            result_list = list(rows)
            
            # Report successful read metrics to Locust
            self._report(operation_name, start_time, response_length=len(result_list))
            
        except Exception as e:
            self._report("ScyllaDB_READ", start_time, exc=e)
            print(f"Error reading data: {e}")

    @task(2)  # Update operations
    @tag("update")
    def update_ecommerce_order(self):
        """Update data (UPDATE operation)"""
        if not inserted_ids:
            return
        
        start_time = datetime.now()
        try:
            random_id = random.choice(inserted_ids)
            new_status = random.choice(ORDER_STATUSES)
            new_total = Decimal(str(round(random.uniform(10.0, 1000.0), 2)))
            
            query = """
            UPDATE ecommerce_orders 
            SET status = %s, total_amount = %s, updated_at = %s
            WHERE id = %s
            """
            
            session.execute(query, (new_status, new_total, datetime.now(), random_id))
            
            # Report successful update metrics to Locust
            self._report("ScyllaDB_UPDATE", start_time)
                
        except Exception as e:
            self._report("ScyllaDB_UPDATE", start_time, exc=e)
            print(f"Error updating data: {e}")

    @task(1)  # Lower weight for deletes
    @tag("delete")
    def delete_ecommerce_order(self):
        """Delete data (DELETE operation)"""
        if not inserted_ids:
            return
        
        start_time = datetime.now()
        try:
            # Remove a random ID from our list and delete it
            if inserted_ids:
                random_id = inserted_ids.pop(random.randint(0, len(inserted_ids) - 1))
                
                query = "DELETE FROM ecommerce_orders WHERE id = %s"
                session.execute(query, (random_id,))
                
                # Report successful delete metrics to Locust
                self._report("ScyllaDB_DELETE", start_time)
                    
        except Exception as e:
            self._report("ScyllaDB_DELETE", start_time, exc=e)
            print(f"Error deleting data: {e}")

    def _random_string(self, length):
        """Generate random alphanumeric string of specified length"""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _report(self, name: str, start_time: datetime, exc: Optional[Exception] = None, response_length: int = 0):
        """Send metrics to Locust for ScyllaDB operations"""
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        self.environment.events.request.fire(
            request_type="ScyllaDB",
            name=name,
            response_time=elapsed_ms,
            response_length=response_length,
            exception=exc,
            context={},
        )

