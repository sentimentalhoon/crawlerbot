import sqlite3
import os

DB_FILE = "crawler.db"

import json

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS posted_items (
            message_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            title TEXT,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # New table for pending items
    c.execute('''
        CREATE TABLE IF NOT EXISTS pending_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            chat_id INTEGER,
            ai_data TEXT,
            image_paths TEXT,
            incident_date TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, chat_id)
        )
    ''')
    conn.commit()
    conn.close()

def is_posted(message_id, chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Check both posted_items and pending_items (if it's already pending, skip re-processing)
    c.execute('SELECT 1 FROM posted_items WHERE message_id = ? AND chat_id = ?', (message_id, chat_id))
    posted = c.fetchone()
    
    if posted:
        conn.close()
        return True
        
    c.execute("SELECT 1 FROM pending_items WHERE message_id = ? AND chat_id = ?", (message_id, chat_id))
    pending = c.fetchone()
    conn.close()
    return pending is not None

def save_posted(message_id, chat_id, title):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO posted_items (message_id, chat_id, title) VALUES (?, ?, ?)', (message_id, chat_id, title))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    conn.close()

def save_pending(message_id, chat_id, ai_data, image_paths, incident_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO pending_items (message_id, chat_id, ai_data, image_paths, incident_date, status) 
            VALUES (?, ?, ?, ?, ?, 'PENDING')
        ''', (message_id, chat_id, json.dumps(ai_data), json.dumps(image_paths), incident_date))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    conn.close()

def get_pending_items():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, message_id, chat_id, ai_data, image_paths, incident_date FROM pending_items WHERE status = 'PENDING'")
    rows = c.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            'id': row[0],
            'message_id': row[1],
            'chat_id': row[2],
            'ai_data': json.loads(row[3]),
            'image_paths': json.loads(row[4]),
            'incident_date': row[5]
        })
    return items

def mark_item_posted(db_id, message_id, chat_id, title):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Update pending status
    c.execute("UPDATE pending_items SET status = 'POSTED' WHERE id = ?", (db_id,))
    
    # Add to posted_items (Legacy / Double check)
    try:
        c.execute('INSERT INTO posted_items (message_id, chat_id, title) VALUES (?, ?, ?)', (message_id, chat_id, title))
    except sqlite3.IntegrityError:
        pass
        
    conn.commit()
    conn.close()
