import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'spse_jobs.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            source_url TEXT NOT NULL,
            job_url TEXT UNIQUE NOT NULL,
            date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
            value TEXT DEFAULT 'Tidak diketahui',
            kbli TEXT DEFAULT 'Tidak diketahui'
        )
    ''')
    
    # Simple migration to add columns if they don't exist in older versions
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN value TEXT DEFAULT 'Tidak diketahui'")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN kbli TEXT DEFAULT 'Tidak diketahui'")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    conn.commit()
    conn.close()

def insert_job(title, category, source_url, job_url, value='Tidak diketahui', kbli='Tidak diketahui'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO jobs (title, category, source_url, job_url, value, kbli)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, category, source_url, job_url, value, kbli))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        # Job already exists
        inserted = False
    conn.close()
    return inserted

def job_exists(job_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM jobs WHERE job_url = ?', (job_url,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def get_all_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM jobs ORDER BY date_added DESC')
    jobs = c.fetchall()
    conn.close()
    return [dict(job) for job in jobs]

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
