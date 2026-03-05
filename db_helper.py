import mysql.connector
from datetime import datetime


# ---------------------------------------------------
# DB CONNECTION
# ---------------------------------------------------
def get_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="pandeyji_eatery",
            autocommit=False
        )
        return conn
    except mysql.connector.Error as e:
        print(f"❌ DATABASE CONNECTION ERROR: {e}")
        return None


# ---------------------------------------------------
# SAFE NEXT ORDER ID (CHECKS BOTH TABLES)
# ---------------------------------------------------
def get_next_order_id():
    try:
        conn = get_connection()
        if not conn:
            return 1

        cur = conn.cursor()

        # Check both orders + order_tracking
        cur.execute("""
            SELECT MAX(order_id) FROM (
                SELECT order_id FROM orders
                UNION
                SELECT order_id FROM order_tracking
            ) AS all_orders
        """)

        row = cur.fetchone()[0]
        cur.close()
        conn.close()

        return 1 if row is None else row + 1

    except mysql.connector.Error as e:
        print("DB ERROR get_next_order_id:", e)
        return 1


# ---------------------------------------------------
# ORDER STATUS
# ---------------------------------------------------
def get_order_status(order_id):
    try:
        conn = get_connection()
        if not conn:
            return None

        cur = conn.cursor()
        cur.execute("SELECT status FROM order_tracking WHERE order_id = %s", (order_id,))
        row = cur.fetchone()

        cur.close()
        conn.close()
        return row[0] if row else None

    except mysql.connector.Error as e:
        print("DB ERROR get_order_status:", e)
        return None


def update_order_status(order_id, new_status):
    try:
        conn = get_connection()
        if not conn:
            return False

        cur = conn.cursor()

        # If no entry exists → insert instead of update
        cur.execute("SELECT 1 FROM order_tracking WHERE order_id=%s", (order_id,))
        exists = cur.fetchone()

        if exists:
            cur.execute(
                "UPDATE order_tracking SET status=%s WHERE order_id=%s",
                (new_status, order_id)
            )
        else:
            cur.execute(
                "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)",
                (order_id, new_status)
            )

        conn.commit()
        cur.close()
        conn.close()
        print(f"✔ Status updated → Order #{order_id}: {new_status}")
        return True

    except mysql.connector.Error as e:
        print("DB ERROR update_order_status:", e)
        return False


def insert_order_tracking(order_id, status):
    try:
        conn = get_connection()
        if not conn:
            return False

        cur = conn.cursor()

        # Prevent duplicate entry errors
        cur.execute("SELECT 1 FROM order_tracking WHERE order_id=%s", (order_id,))
        if cur.fetchone():
            # If already exists, UPDATE instead of INSERT
            cur.execute("UPDATE order_tracking SET status=%s WHERE order_id=%s",
                        (status, order_id))
        else:
            cur.execute(
                "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)",
                (order_id, status)
            )

        conn.commit()
        cur.close()
        conn.close()

        print(f"✔ Tracking inserted/updated → {order_id}: {status}")
        return True

    except mysql.connector.Error as e:
        print("DB ERROR insert_order_tracking:", e)
        return False


# ---------------------------------------------------
# ORDER ITEM INSERTION
# ---------------------------------------------------
def insert_order_item(food_item, qty, order_id):
    try:
        if isinstance(food_item, list):
            food_item = food_item[0]

        conn = get_connection()
        if not conn:
            return False

        cur = conn.cursor()

        # Case-insensitive match
        cur.execute(
            "SELECT item_id, price FROM food_items WHERE LOWER(name)=LOWER(%s)",
            (food_item,)
        )
        item_data = cur.fetchone()

        if not item_data:
            print(f"❌ Food item not found: {food_item}")
            cur.close()
            conn.close()
            return False

        item_id, price = item_data
        total_price = price * qty

        cur.execute("""
            INSERT INTO orders (order_id, item_id, quantity, total_price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, item_id, qty, total_price))

        conn.commit()
        print(f"✔ {qty} × {food_item} (₹{total_price}) added to order #{order_id}")

        cur.close()
        conn.close()
        return True

    except mysql.connector.Error as e:
        print(f"DB ERROR insert_order_item for {food_item}: {e}")
        return False


# ---------------------------------------------------
# ORDER TOTAL
# ---------------------------------------------------
def get_total_order_price(order_id):
    try:
        conn = get_connection()
        if not conn:
            return 0

        cur = conn.cursor()

        cur.execute(
            "SELECT SUM(total_price) FROM orders WHERE order_id=%s",
            (order_id,)
        )
        total = cur.fetchone()[0]

        cur.close()
        conn.close()
        return total or 0

    except mysql.connector.Error as e:
        print("DB ERROR get_total_order_price:", e)
        return 0


# ---------------------------------------------------
# ORDER DETAILS
# ---------------------------------------------------
def get_order_details(order_id):
    try:
        conn = get_connection()
        if not conn:
            return []

        cur = conn.cursor()
        cur.execute("""
            SELECT f.name, o.quantity, f.price, o.total_price
            FROM orders o
            JOIN food_items f ON o.item_id = f.item_id
            WHERE o.order_id=%s
        """, (order_id,))

        rows = cur.fetchall()

        cur.close()
        conn.close()
        return rows

    except mysql.connector.Error as e:
        print("DB ERROR get_order_details:", e)
        return []


# ---------------------------------------------------
# REMOVE ITEM
# ---------------------------------------------------
def remove_item_from_order(order_id, food_item):
    try:
        if isinstance(food_item, list):
            food_item = food_item[0]

        conn = get_connection()
        if not conn:
            return False

        cur = conn.cursor()

        cur.execute(
            "SELECT item_id FROM food_items WHERE LOWER(name)=LOWER(%s)",
            (food_item,)
        )
        row = cur.fetchone()

        if not row:
            print(f"❌ Menu item not found: {food_item}")
            cur.close()
            conn.close()
            return False

        item_id = row[0]

        cur.execute("""
            SELECT quantity, total_price
            FROM orders
            WHERE order_id=%s AND item_id=%s
        """, (order_id, item_id))
        item_data = cur.fetchone()

        if not item_data:
            print(f"❌ {food_item} not found in order #{order_id}")
            cur.close()
            conn.close()
            return False

        quantity, total_price = item_data

        cur.execute(
            "DELETE FROM orders WHERE order_id=%s AND item_id=%s",
            (order_id, item_id)
        )
        conn.commit()

        print(f"✔ Removed {quantity} × {food_item} from order #{order_id}")

        cur.execute("SELECT COUNT(*) FROM orders WHERE order_id=%s", (order_id,))
        remaining = cur.fetchone()[0]

        if remaining == 0:
            update_order_status(order_id, "cancelled")
            print(f"✔ Order #{order_id} became empty → CANCELLED")

        cur.close()
        conn.close()
        return True

    except mysql.connector.Error as e:
        print("DB ERROR remove_item_from_order:", e)
        return False


# ---------------------------------------------------
# CHECKPOINTS
# ---------------------------------------------------
def add_order_checkpoint(order_id, checkpoint_name):
    try:
        conn = get_connection()
        if not conn:
            return False

        cur = conn.cursor()

        cur.execute("SELECT 1 FROM order_tracking WHERE order_id=%s", (order_id,))
        if not cur.fetchone():
            print(f"❌ Order #{order_id} does not exist")
            cur.close()
            conn.close()
            return False

        cur.execute("""
            INSERT INTO order_checkpoints (order_id, checkpoint_name)
            VALUES (%s, %s)
        """, (order_id, checkpoint_name))

        conn.commit()
        cur.close()
        conn.close()
        print(f"✔ Checkpoint added → {order_id}: {checkpoint_name}")
        return True

    except mysql.connector.Error as e:
        print("DB ERROR add_order_checkpoint:", e)
        return False


def get_order_checkpoints(order_id):
    try:
        conn = get_connection()
        if not conn:
            return []

        cur = conn.cursor()
        cur.execute("""
            SELECT checkpoint_name, timestamp
            FROM order_checkpoints
            WHERE order_id=%s
            ORDER BY timestamp
        """, (order_id,))

        rows = cur.fetchall()

        cur.close()
        conn.close()
        return rows

    except mysql.connector.Error as e:
        print("DB ERROR get_order_checkpoints:", e)
        return []


# ---------------------------------------------------
# CANCEL PERMISSION
# ---------------------------------------------------
def can_cancel_order(order_id):
    try:
        checkpoints = get_order_checkpoints(order_id)

        if not checkpoints:
            return True

        last_checkpoint = checkpoints[-1][0].lower()

        if "out for delivery" in last_checkpoint:
            return False
        if "delivered" in last_checkpoint:
            return False
        if "cancelled" in last_checkpoint:
            return False

        return True

    except Exception as e:
        print(f"Error in can_cancel_order: {e}")
        return False


# ---------------------------------------------------
# ADMIN: ALL ORDERS
# ---------------------------------------------------
def get_all_orders():
    try:
        conn = get_connection()
        if not conn:
            return []

        cur = conn.cursor()
        cur.execute("""
            SELECT o.order_id, f.name, o.quantity, o.total_price, t.status
            FROM orders o
            JOIN food_items f ON o.item_id = f.item_id
            JOIN order_tracking t ON o.order_id = t.order_id
            ORDER BY o.order_id
        """)

        rows = cur.fetchall()

        cur.close()
        conn.close()
        return rows

    except mysql.connector.Error as e:
        print("DB ERROR get_all_orders:", e)
        return []
