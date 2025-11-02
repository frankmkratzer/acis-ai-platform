#!/usr/bin/env python3
"""Show all clients in database"""
import psycopg2

conn = psycopg2.connect(
    host="localhost", database="acis-ai", user="postgres", password="$@nJose420"
)

cur = conn.cursor()
cur.execute(
    """
    SELECT client_id, first_name, last_name, email, phone, risk_tolerance, is_active, created_at
    FROM clients
    ORDER BY client_id
"""
)

clients = cur.fetchall()

print("=" * 100)
print("CLIENTS IN DATABASE")
print("=" * 100)
print()

if clients:
    for client in clients:
        print(f"Client ID: {client[0]}")
        print(f"Name: {client[1]} {client[2]}")
        print(f"Email: {client[3]}")
        print(f"Phone: {client[4] or 'N/A'}")
        print(f"Risk Tolerance: {client[5] or 'N/A'}")
        print(f"Active: {client[6]}")
        print(f"Created: {client[7]}")
        print("-" * 100)
else:
    print("No clients found!")

print()
cur.close()
conn.close()
