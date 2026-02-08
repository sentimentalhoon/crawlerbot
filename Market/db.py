import sqlite3
import datetime

DB_NAME = 'crawled_data.db'

def init_db():
    """Initialize the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            title TEXT,
            crawled_at TIMESTAMP,
            posted_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_posted(post_id):
    """Check if a post_id has already been processed."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM posts WHERE id = ?', (post_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_post(post_id, title):
    """Save a new post record."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    cursor.execute('''
        INSERT INTO posts (id, title, crawled_at, posted_at)
        VALUES (?, ?, ?, ?)
    ''', (post_id, title, now, now))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database {DB_NAME} initialized.")
