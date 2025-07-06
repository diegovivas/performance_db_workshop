import os

from cassandra.cluster import Cluster, DCAwareRoundRobinPolicy
from dotenv import load_dotenv

load_dotenv()


def create_table():
    try:
        cassandra_contact_points = os.getenv(
            "CASSANDRA_CONTACT_POINTS", "127.0.0.1"
        ).split(",")
        cassandra_port = int(os.getenv("CASSANDRA_PORT", 9042))
        cassandra_keyspace = os.getenv("CASSANDRA_KEYSPACE", "ecommerce_keyspace")
        cassandra_local_dc = os.getenv("CASSANDRA_LOCAL_DC", "datacenter1")

        cluster = Cluster(
            cassandra_contact_points,
            port=cassandra_port,
            load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=cassandra_local_dc),
        )

        session = cluster.connect()
        
        # Create keyspace
        session.execute(
            f"""
            CREATE KEYSPACE IF NOT EXISTS {cassandra_keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}}
            """
        )
        
        session.set_keyspace(cassandra_keyspace)
        
        # Create ecommerce_orders table
        session.execute(
            """
            CREATE TABLE IF NOT EXISTS ecommerce_orders (
                id UUID PRIMARY KEY,
                user_id UUID,
                order_number TEXT,
                customer_email TEXT,
                total_amount DECIMAL,
                status TEXT,
                payment_method TEXT,
                shipping_address TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                items_count INT,
                is_express_shipping BOOLEAN,
                discount_code TEXT,
                tax_amount DECIMAL
            )
            """
        )
        

        print(f"ScyllaDB keyspace '{cassandra_keyspace}' and table 'ecommerce_orders' created successfully.")
        
    except Exception as e:
        print(f"Error creating ScyllaDB table: {e}")
    finally:
        if 'session' in locals():
            session.shutdown()
        if 'cluster' in locals():
            cluster.shutdown()


if __name__ == "__main__":
    create_table()
