from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import db_helper
import generic_helper
import re
import uvicorn
import json
import time
import smtplib
from email.mime.text import MIMEText


app = FastAPI()

# ---------------------------------------------------
# CORS — Allow all for testing
# ---------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store ongoing orders per session (Dialogflow only)
in_progress_orders = {}

# ---------------------------------------------------
#  EMAIL SETTINGS
# ---------------------------------------------------
OWNER_EMAIL = "22becse42.cse@cujammu.ac.in"
SMTP_USER  = "22becse42.cse@cujammu.ac.in"
SMTP_PASS  = "tgkn fzgy fdec tetw"   # app password

def send_mail(subject, message):
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = OWNER_EMAIL

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, OWNER_EMAIL, msg.as_string())
        print("📧 Email sent:", subject)
    except Exception as e:
        print("❌ Email error:", e)


# ---------------------------------------------------
# Helper: Extract session info from Dialogflow
# ---------------------------------------------------
def extract_session_info(payload: dict):
    main_session = payload.get("session", "")
    if main_session and "/sessions/" in main_session:
        try:
            short = main_session.split("/sessions/")[1].split("/")[0]
            return main_session, short
        except:
            pass

    query_result = payload.get("queryResult", {})
    ctxs = query_result.get("outputContexts", [])
    if ctxs:
        for ctx in ctxs:
            name = ctx.get("name", "")
            if "/sessions/" in name:
                short = name.split("/sessions/")[1].split("/")[0]
                prefix = name.split("/sessions/")[0]
                full = prefix + "/sessions/" + short
                return full, short

    fallback = f"local-{int(time.time()*1000)}"
    return "", fallback


# ---------------------------------------------------
# INTENT HANDLERS
# ---------------------------------------------------
def new_order_intent(session_id):
    in_progress_orders[session_id] = {}
    return {"fulfillmentText": "Great! Starting a fresh order. Tell me items you want."}


def add_to_order(parameters, session_id):
    try:
        food_items = parameters.get("food-item", [])
        quantities = parameters.get("number", [])

        if food_items and isinstance(food_items[0], list):
            food_items = [fi[0] for fi in food_items]
        if quantities and isinstance(quantities[0], list):
            quantities = [int(q[0]) for q in quantities]
        else:
            quantities = [int(q) for q in quantities] if quantities else []

        if len(food_items) != len(quantities):
            return {"fulfillmentText": "Please specify quantity clearly for each item."}

        if session_id not in in_progress_orders:
            in_progress_orders[session_id] = {}
        order_dict = in_progress_orders[session_id]

        for item, qty in zip(food_items, quantities):
            item = str(item).strip()
            order_dict[item] = order_dict.get(item, 0) + qty

        order_str = generic_helper.get_str_from_food_dict(order_dict)

        return {"fulfillmentText": f"Added! So far: {order_str}. Want to add more?"}

    except Exception as e:
        print("❌ add_to_order ERROR:", e)
        return {"fulfillmentText": "Error adding items."}


def complete_order(session_id, background_tasks: BackgroundTasks):
    try:
        if session_id not in in_progress_orders:
            return {"fulfillmentText": "No active order."}

        order = in_progress_orders[session_id]
        if not order:
            return {"fulfillmentText": "Your order is empty."}

        order_id = db_helper.get_next_order_id()

        for item, qty in order.items():
            if not db_helper.insert_order_item(item, qty, order_id):
                return {"fulfillmentText": f"Error adding {item}."}

        db_helper.insert_order_tracking(order_id, "in progress")
        total = db_helper.get_total_order_price(order_id)

        # ---------------------------
        # 📧 EMAIL — ORDER PLACED (background)
        # ---------------------------
        items_text = "\n".join([f"- {i} x {q}" for i, q in order.items()])
        email_body = f"""
New order received!

Order ID: {order_id}
Total Amount: ₹{total}

Items:
{items_text}

Track: http://localhost:8000/api/track-order/{order_id}
Show:  http://localhost:8000/api/show-order/{order_id}
Cancel: http://localhost:8000/api/cancel-order/{order_id}
"""

        background_tasks.add_task(send_mail, f"Chatbot Order #{order_id}", email_body)

        del in_progress_orders[session_id]

        return {"fulfillmentText": f"Order placed! ID #{order_id}. Total ₹{total}."}

    except Exception as e:
        print("❌ complete_order ERROR:", e)
        return {"fulfillmentText": "Error completing order."}


def remove_from_ongoing_order(parameters, session_id):
    try:
        item_list = parameters.get("food-item", [])
        item = item_list[0] if item_list else None

        if not item:
            return {"fulfillmentText": "Which item to remove?"}

        if session_id not in in_progress_orders:
            return {"fulfillmentText": "No active order to remove items."}

        order_dict = in_progress_orders[session_id]

        if item not in order_dict:
            return {"fulfillmentText": f"{item} not in your order."}

        del order_dict[item]

        if not order_dict:
            del in_progress_orders[session_id]
            return {"fulfillmentText": "Item removed. Order empty now."}

        order_str = generic_helper.get_str_from_food_dict(order_dict)
        return {"fulfillmentText": f"Removed {item}. Now you have: {order_str}."}

    except Exception as e:
        print("❌ remove_from_ongoing_order ERROR:", e)
        return {"fulfillmentText": "Error removing item."}


def remove_existing_item(parameters):
    try:
        order_id = parameters.get("number")
        item = parameters.get("food-item")

        if isinstance(order_id, list):
            order_id = order_id[0]
        if isinstance(item, list):
            item = item[0]

        order_id = int(order_id)

        success = db_helper.remove_item_from_order(order_id, item)

        if success:
            return {"fulfillmentText": f"Removed {item} from order #{order_id}."}
        return {"fulfillmentText": f"{item} not found in order #{order_id}."}

    except:
        return {"fulfillmentText": "Error removing item."}


def show_order(parameters, session_id, session_path):
    try:
        order_id = parameters.get("number")
        if isinstance(order_id, list):
            order_id = order_id[0]

        order_id = int(order_id)

        details = db_helper.get_order_details(order_id)
        if not details:
            return {"fulfillmentText": f"No details for #{order_id}."}

        checkpoints = db_helper.get_order_checkpoints(order_id)
        status = db_helper.get_order_status(order_id)

        msg = f"📦 Order #{order_id} — Status: {status.upper()}\n\n"

        if checkpoints:
            msg += "🚚 Progress:\n"
            for c in checkpoints:
                msg += f"• {c[0]} — {c[1]}\n"
            msg += "\n"

        msg += "🍽 Items:\n"
        for d in details:
            msg += f"• {d[0]} — {d[1]} × ₹{d[2]} = ₹{d[3]}\n"

        msg += f"\n💰 Total: ₹{db_helper.get_total_order_price(order_id)}"

        output_contexts = []
        if session_path:
            output_contexts = [{
                "name": f"{session_path}/contexts/existing-order",
                "lifespanCount": 5,
                "parameters": {"number": order_id}
            }]

        return {"fulfillmentText": msg, "outputContexts": output_contexts}

    except:
        return {"fulfillmentText": "Error showing order."}


def cancel_order(parameters, background_tasks: BackgroundTasks):
    try:
        order_id = parameters.get("number")
        if isinstance(order_id, list):
            order_id = order_id[0]
        order_id = int(order_id)

        if not db_helper.can_cancel_order(order_id):
            return {"fulfillmentText": "Cannot cancel this order."}

        db_helper.update_order_status(order_id, "cancelled")

        # ---------------------------
        # 📧 EMAIL — ORDER CANCELLED (background)
        # ---------------------------
        email_body = f"""
Order Cancelled!

Order ID: {order_id}

Track: http://localhost:8000/api/track-order/{order_id}
Show:  http://localhost:8000/api/show-order/{order_id}
"""

        background_tasks.add_task(send_mail, f"Chatbot: Order Cancelled #{order_id}", email_body)

        return {"fulfillmentText": f"Order #{order_id} cancelled."}

    except:
        return {"fulfillmentText": "Error cancelling order."}


def track_order(parameters, query_text):
    try:
        order_id = parameters.get("number")

        # ✅ If no order ID provided → ask politely
        if not order_id:
            return {"fulfillmentText": "May I have your order ID, please?"}

        # Dialogflow sometimes sends list
        if isinstance(order_id, list):
            order_id = order_id[0]

        order_id = int(order_id)

        status = db_helper.get_order_status(order_id)
        if not status:
            return {"fulfillmentText": f"No order found with ID #{order_id}."}

        details = db_helper.get_order_details(order_id)
        items_count = sum([d[1] for d in details]) if details else 0

        return {
            "fulfillmentText": f"📦 Order #{order_id} is **{status.upper()}**\nTotal Items: {items_count}"
        }

    except Exception as e:
        print("Track Order Error:", e)
        return {"fulfillmentText": "Something went wrong while tracking your order."}


def track_progress(parameters):
    try:
        order_id = int(parameters.get("number"))
        checkpoints = db_helper.get_order_checkpoints(order_id)
        if not checkpoints:
            return {"fulfillmentText": f"No delivery updates for #{order_id}."}

        msg = f"🚚 Progress for #{order_id}:\n"
        for c in checkpoints:
            msg += f"• {c[0]} — {c[1]}\n"

        return {"fulfillmentText": msg}

    except:
        return {"fulfillmentText": "Error getting progress."}


def add_checkpoint(parameters):
    try:
        order_id = int(parameters.get("number"))
        checkpoint = parameters.get("checkpoint", "Order processed")

        if isinstance(checkpoint, list):
            checkpoint = checkpoint[0]

        success = db_helper.add_order_checkpoint(order_id, checkpoint)

        if success:
            return {"fulfillmentText": f"Added checkpoint '{checkpoint}' for #{order_id}."}

        return {"fulfillmentText": f"Could not add checkpoint."}

    except:
        return {"fulfillmentText": "Error adding checkpoint."}



# ---------------------------------------------------
# WEBHOOK
# ---------------------------------------------------
@app.post("/webhook")
async def dialogflow_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        print("📥 Webhook received:\n", json.dumps(payload, indent=2))

        query_result = payload.get("queryResult", {})
        intent = query_result.get("intent", {}).get("displayName", "")
        parameters = query_result.get("parameters", {})
        query_text = query_result.get("queryText", "")

        session_path, session_id = extract_session_info(payload)

        print("Intent:", intent)
        print("Session:", session_id)

        # Use startswith for robust matching of displayName variations
        if intent.startswith("new.order"):
            return new_order_intent(session_id)

        elif intent.startswith("order.add"):
            # ensure we only treat ongoing-order variant as add-to-order
            # (Dialogflow sometimes appends context info to displayName)
            return add_to_order(parameters, session_id)

        elif intent.startswith("order.complete"):
            return complete_order(session_id, background_tasks)

        elif intent.startswith("order.remove") and "ongoing-order" in intent:
            return remove_from_ongoing_order(parameters, session_id)

        elif intent.startswith("order.remove") and "existing-order" in intent:
            return remove_existing_item(parameters)

        elif intent.startswith("order.show"):
            return show_order(parameters, session_id, session_path)

        elif intent.startswith("order.cancel"):
            return cancel_order(parameters, background_tasks)


        elif intent.startswith("order.add_checkpoint"):
            return add_checkpoint(parameters)

        elif intent.startswith("track.order"):
            return track_order(parameters, query_text)

        elif intent.startswith("track.progress"):
            return track_progress(parameters)

        return {"fulfillmentText": "Sorry, I didn't understand that."}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        # return a simple message so Dialogflow doesn't timeout silently
        return {"fulfillmentText": "Server error while processing webhook."}



# ---------------------------------------------------
# REST API (WEBSITE)
# ---------------------------------------------------
@app.post("/api/create-order")
async def api_create_order(payload: dict, background_tasks: BackgroundTasks):
    try:
        items = payload.get("items", [])
        if not items:
            return {"success": False, "message": "No items provided"}

        order_id = db_helper.get_next_order_id()

        for it in items:
            name = it.get("name")
            qty = it.get("quantity")
            if qty > 0:
                db_helper.insert_order_item(name, qty, order_id)

        db_helper.insert_order_tracking(order_id, "in progress")
        total = db_helper.get_total_order_price(order_id)

        lines = "\n".join([f"- {i['name']} x {i['quantity']}" for i in items])

        email_body = f"""
New order received!

Order ID: {order_id}
Total Amount: ₹{total}

Items:
{lines}

Track: http://localhost:8000/api/track-order/{order_id}
Show:  http://localhost:8000/api/show-order/{order_id}
Cancel: http://localhost:8000/api/cancel-order/{order_id}
"""
        background_tasks.add_task(send_mail, f"New Order Placed #{order_id}", email_body)

        return {"success": True, "order_id": order_id, "total": total}

    except Exception as e:
        print("API create_order ERROR:", e)
        return {"success": False, "message": "Server error"}


# ---------------------------------------------------
# TRACK ORDER (STEP 6 — send mail)
# ---------------------------------------------------
@app.get("/api/track-order/{order_id}")
async def api_track_order(order_id: int, background_tasks: BackgroundTasks):
    status = db_helper.get_order_status(order_id)
    if not status:
        return {"success": False, "message": "Order not found"}

    background_tasks.add_task(
        send_mail,
        f"Track Order #{order_id}",
        f"Order #{order_id} is currently '{status.upper()}'."
    )

    return {"success": True, "order_id": order_id, "status": status}


# ---------------------------------------------------
# SHOW ORDER  (optional email)
# ---------------------------------------------------
@app.get("/api/show-order/{order_id}")
async def api_show_order(order_id: int):
    details = db_helper.get_order_details(order_id)
    if not details:
        return {"success": False, "message": "Order not found"}

    return {
        "success": True,
        "order_id": order_id,
        "status": db_helper.get_order_status(order_id),
        "items": details,
        "checkpoints": db_helper.get_order_checkpoints(order_id),
        "total": db_helper.get_total_order_price(order_id)
    }


# ---------------------------------------------------
# CANCEL ORDER (STEP 4 — send mail)
# ---------------------------------------------------
@app.post("/api/cancel-order/{order_id}")
async def api_cancel_order(order_id: int, background_tasks: BackgroundTasks):
    if not db_helper.can_cancel_order(order_id):
        return {"success": False, "message": "Cannot cancel order"}

    db_helper.update_order_status(order_id, "cancelled")

    background_tasks.add_task(
        send_mail,
        f"Order #{order_id} Cancelled",
        f"Order #{order_id} has been cancelled."
    )

    return {"success": True, "message": f"Order #{order_id} cancelled"}


# ---------------------------------------------------
# REMOVE ITEM (STEP 5 — send mail)
# ---------------------------------------------------
@app.post("/api/remove-item")
async def api_remove_item(payload: dict, background_tasks: BackgroundTasks):
    order_id = payload.get("order_id")
    item = payload.get("item")

    if not order_id or not item:
        return {"success": False, "message": "Order ID and item needed"}

    ok = db_helper.remove_item_from_order(order_id, item)

    if ok:
        background_tasks.add_task(
            send_mail,
            f"Item removed from #{order_id}",
            f"Removed: {item}\nOrder ID: {order_id}"
        )
        return {"success": True, "message": f"Removed {item} from order #{order_id}"}
    else:
        return {"success": False, "message": "Item not found"}



# ---------------------------------------------------
# SERVER START
# ---------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "Server running"}


if __name__ == "__main__":
    print("🚀 Food Chatbot Server Started")
    uvicorn.run(app, host="0.0.0.0", port=8000)
