"""
Locust load-test script (estrategia 2.A – compatible con Python 3.9)

• Cada task obtiene un cursor del pool y lo devuelve inmediatamente.
• Pool real: 20 conexiones -> soporta cientos o miles de VUs.
• Guarda hasta 10k IDs para pruebas de lectura, actualización y borrado.
"""

import os
import random
import string
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional  # Para Python < 3.10

import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from locust import User, between, task


# E-commerce data for realistic testing
ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]
PAYMENT_METHODS = ["credit_card", "paypal", "bank_transfer", "apple_pay", "google_pay"]
DISCOUNT_CODES = [None, "SAVE10", "WELCOME20", "BLACKFRIDAY", "SUMMER25", "FREESHIP"]
CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", 
          "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville"]


# ─────────────────────────── Configuración ────────────────────────────
load_dotenv()  # Lee variables de .env si existen

postgres_config = {
    "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "testdb"),
    "user": os.getenv("POSTGRES_USER", "testuser"),
    "password": os.getenv("POSTGRES_PASSWORD", "testpass"),
    "connect_timeout": 10,
    "application_name": "locust_load_test",
}

# Crea un pool pequeño (20) para miles de usuarios virtuales
postgres_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    **postgres_config,
)

inserted_ids: list[str] = []  # IDs para otras operaciones

# ─────────────────────────── Usuario de Locust ─────────────────────────
class PostgresUser(User):
    wait_time = between(0.1, 1)  # think-time aleatorio

    # ---------- Context manager: cursor + devolución al pool ----------
    @contextmanager
    def _cursor(self):
        conn = postgres_pool.getconn()
        try:
            conn.autocommit = True
            cur = conn.cursor()
            yield cur
        finally:
            cur.close()
            postgres_pool.putconn(conn)

    # ----------------------------- INSERT -----------------------------
    @task(4)
    def insert_data(self):
        """CREATE"""
        record_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        # Generate unique order number using UUID to avoid duplicates
        order_number = f"{str(uuid.uuid4())[:20].upper()}"
        start = datetime.now()

        try:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ecommerce_orders (
                        id, user_id, order_number, customer_email, total_amount, status,
                        payment_method, shipping_address, created_at, updated_at, items_count,
                        is_express_shipping, discount_code, tax_amount
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
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
                    ),
                )

            if len(inserted_ids) < 10_000:
                inserted_ids.append(record_id)

            self._report("INSERT", start)
        except Exception as e:
            self._report("INSERT", start, e)

    # ----------------------------- SELECT -----------------------------
    @task(3)
    def read_data(self):
        """READ"""
        start = datetime.now()
        try:
            # Random query patterns - same as ScyllaDB
            query_type = random.choice(['by_id', 'by_status', 'random_sample'])
            
            with self._cursor() as cur:
                if query_type == 'by_id' and inserted_ids:
                    cur.execute(
                        "SELECT * FROM ecommerce_orders WHERE id = %s",
                        (random.choice(inserted_ids),),
                    )
                    operation_name = "SELECT_BY_ID"
                elif query_type == 'by_status':
                    status = random.choice(ORDER_STATUSES)
                    cur.execute(
                        "SELECT * FROM ecommerce_orders WHERE status = %s LIMIT 100",
                        (status,),
                    )
                    operation_name = "SELECT_BY_STATUS"
                else:  # random_sample
                    cur.execute("SELECT * FROM ecommerce_orders LIMIT 50")
                    operation_name = "SELECT_SAMPLE"

                result_list = cur.fetchall()  # consumir resultado

            self._report(operation_name, start, response_length=len(result_list))
        except Exception as e:
            self._report("SELECT", start, e)

    # ----------------------------- UPDATE -----------------------------
    @task(2)
    def update_data(self):
        """UPDATE"""
        if not inserted_ids:
            return

        start = datetime.now()
        try:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE ecommerce_orders
                    SET status = %s,
                        total_amount = %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        random.choice(ORDER_STATUSES),
                        Decimal(str(round(random.uniform(10.0, 1000.0), 2))),
                        datetime.now(),
                        random.choice(inserted_ids),
                    ),
                )

            self._report("UPDATE", start)
        except Exception as e:
            self._report("UPDATE", start, e)

    # ----------------------------- DELETE -----------------------------
    @task(1)
    def delete_data(self):
        """DELETE"""
        if not inserted_ids:
            return

        start = datetime.now()
        try:
            with self._cursor() as cur:
                cur.execute(
                    "DELETE FROM ecommerce_orders WHERE id = %s",
                    (inserted_ids.pop(random.randrange(len(inserted_ids))),),
                )

            self._report("DELETE", start)
        except Exception as e:
            self._report("DELETE", start, e)

    # ─────────────────────────── Helpers ────────────────────────────
    @staticmethod
    def _rnd(length: int) -> str:
        """Random alfanumérico de `length` caracteres"""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _report(self, name: str, start: datetime, exc: Optional[Exception] = None, response_length: int = 0):
        """Send metrics to Locust"""
        elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)
        self.environment.events.request.fire(
            request_type="SQL",
            name=name,
            response_time=elapsed_ms,
            response_length=response_length,
            exception=exc,
            context={},
        )
