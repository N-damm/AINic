# database.py
import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.setup_tables()
        
    def setup_tables(self):
        cursor = self.conn.cursor()
        
        # Tabla de productos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                mla_id TEXT PRIMARY KEY,
                title TEXT,
                price REAL,
                stock INTEGER,
                last_update TIMESTAMP
            )
        """)
        
        # Tabla de ventas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id TEXT PRIMARY KEY,
                mla_id TEXT,
                price REAL,
                quantity INTEGER,
                date TIMESTAMP,
                FOREIGN KEY (mla_id) REFERENCES products (mla_id)
            )
        """)
        
        # Tabla de precios históricos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mla_id TEXT,
                price REAL,
                date TIMESTAMP,
                FOREIGN KEY (mla_id) REFERENCES products (mla_id)
            )
        """)
        
        self.conn.commit()
        
    def update_product(self, mla_id, title, price, stock):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO products 
            (mla_id, title, price, stock, last_update)
            VALUES (?, ?, ?, ?, ?)
        """, (mla_id, title, price, stock, datetime.now()))
        
        cursor.execute("""
            INSERT INTO price_history 
            (mla_id, price, date)
            VALUES (?, ?, ?)
        """, (mla_id, price, datetime.now()))
        
        self.conn.commit()
        
    def get_products(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM products")
        return cursor.fetchall()
        
    def get_price_history(self, mla_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT price, date 
            FROM price_history 
            WHERE mla_id = ?
            ORDER BY date DESC
        """, (mla_id,))
        return cursor.fetchall()