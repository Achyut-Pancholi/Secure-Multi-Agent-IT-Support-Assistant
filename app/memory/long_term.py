import sqlite3
import json
from typing import Dict, Any, Optional
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "memory", "long_term.db")

def init_db():
    """Initialize the SQLite database for long-term memory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_memory (
                user_id TEXT PRIMARY KEY,
                attributes TEXT
            )
        ''')
        conn.commit()

def get_user_memory(user_id: str) -> Dict[str, Any]:
    """Retrieve long-term memory for a user."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT attributes FROM user_memory WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}

def save_user_memory(user_id: str, attributes: Dict[str, Any]):
    """Save or overwrite long-term memory for a user."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO user_memory (user_id, attributes) VALUES (?, ?)',
            (user_id, json.dumps(attributes))
        )
        conn.commit()

def update_user_memory(user_id: str, new_attributes: Dict[str, Any]):
    """Merge new attributes into existing user memory."""
    current_memory = get_user_memory(user_id)
    current_memory.update(new_attributes)
    save_user_memory(user_id, current_memory)

# Initialize on import
init_db()

