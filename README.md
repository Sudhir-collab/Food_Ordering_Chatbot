🍽️ AI Food Ordering Chatbot with Website

An AI-powered food ordering system that allows users to place and manage restaurant orders through:

🤖 Dialogflow Chatbot

🌐 Website Interface

⚡ FastAPI Backend

🗄️ MySQL Database

The system supports order creation, tracking, modification, cancellation, and progress updates, while also sending email notifications to the restaurant owner.

📌 Project Features
🤖 Chatbot Ordering

Customers can order food using a chatbot connected to Dialogflow.

Supported chatbot actions:

Start a new order

Add items

Remove items

Complete order

Track order

Cancel order

Show order details

The chatbot communicates with the backend via a Dialogflow webhook implemented in FastAPI. 

main

🌐 Website Ordering

Customers can also order through a web interface.

Features include:

Interactive food menu

Quantity selection

Cart system

Place order

Track order

Show order

Cancel order

Remove item from order

The website communicates with backend APIs such as:

/api/create-order

/api/track-order/{id}

/api/show-order/{id}

/api/cancel-order/{id} 

main

📧 Email Notifications

Whenever important actions occur, the system automatically sends email notifications:

Order placed

Order cancelled

Order tracked

Item removed from order

Emails are sent using SMTP via Gmail.

📦 Order Tracking System

Each order contains:

Order ID

Order status

Ordered items

Total price

Delivery checkpoints

Checkpoints allow tracking delivery progress such as:

Order prepared

Out for delivery

Delivered

🏗️ System Architecture
User (Website / Chatbot)
          │
          ▼
     FastAPI Backend
          │
          ▼
      MySQL Database
          │
          ▼
    Email Notification System
📂 Project Structure
project/
│
├── main.py
├── db_helper.py
├── generic_helper.py
├── index.html
├── pandeyji_eatery.sql
│
└── assets
    ├── food images
    └── logo
📄 File Description
main.py

Main FastAPI server.

Responsibilities:

Dialogflow webhook

REST API endpoints

Order processing

Email notifications

Session order management

Runs the backend server using Uvicorn. 

main

db_helper.py

Handles all database operations.

Functions include:

Database connection

Insert order items

Get order status

Get order details

Remove item from order

Cancel order

Add checkpoints

Fetch all orders

Uses MySQL Connector for Python. 

db_helper

generic_helper.py

Contains helper utilities such as:

Extracting session IDs

Converting order dictionaries into readable strings

These functions help manage chatbot sessions and format order messages. 

generic_helper

index.html

The frontend website that provides:

Restaurant menu

Interactive ordering system

Cart management

API-based order actions

It also integrates Dialogflow Messenger chatbot widget for conversational ordering. 

index

pandeyji_eatery.sql

SQL script that creates the database structure including:

Tables:

food_items

orders

order_tracking

Also includes:

Stored procedures

Functions for calculating prices and totals. 

pandeyji_eatery

🗄️ Database Schema
food_items

Stores restaurant menu items.

item_id
name
price
orders

Stores order item details.

order_id
item_id
quantity
total_price
order_tracking

Stores order status.

order_id
status
⚙️ Installation Guide
1️⃣ Clone the repository
git clone https://github.com/yourusername/food-chatbot.git
cd food-chatbot
2️⃣ Install dependencies
pip install fastapi uvicorn mysql-connector-python
3️⃣ Setup MySQL Database

Import the SQL file:

pandeyji_eatery.sql

This will automatically create:

Database

Tables

Stored procedures

4️⃣ Configure database credentials

Edit in db_helper.py:

host="localhost"
user="root"
password="root"
database="pandeyji_eatery"
5️⃣ Configure Email Settings

Edit in main.py:

OWNER_EMAIL = "your_email"
SMTP_USER = "your_email"
SMTP_PASS = "gmail_app_password"
6️⃣ Run the Server
python main.py

or

uvicorn main:app --reload

Server runs on:

http://localhost:8000
🌐 API Endpoints
Create Order
POST /api/create-order
Track Order
GET /api/track-order/{order_id}
Show Order
GET /api/show-order/{order_id}
Cancel Order
POST /api/cancel-order/{order_id}
Remove Item
POST /api/remove-item
🤖 Chatbot Integration

The chatbot uses Dialogflow Webhook.

Webhook endpoint:

POST /webhook

Handled intents include:

new.order

order.add

order.complete

order.remove

order.show

order.cancel

track.order

track.progress

🚀 Example Order Flow

1️⃣ Customer opens website or chatbot
2️⃣ Selects food items
3️⃣ Order is created in database
4️⃣ Email notification is sent
5️⃣ Customer can track or modify order

🛠️ Technologies Used

Backend

Python

FastAPI

Uvicorn

Frontend

HTML

JavaScript

Dialogflow Messenger

Database

MySQL

Other Tools

SMTP Email

Dialogflow NLP

📈 Future Improvements

User authentication

Online payments

Admin dashboard

Real-time delivery tracking

Mobile application

👨‍💻 Author

Sudhir
Computer Science Engineering Student
