from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# Initialize the database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )''')
    
    # Insert some test data
    cursor.execute("INSERT OR IGNORE INTO users (id, username, password) VALUES (1, 'admin', 'admin123')")
    cursor.execute("INSERT OR IGNORE INTO users (id, username, password) VALUES (2, 'user', 'password123')")
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return "Vulnerable API - Don't use this in production!"

@app.route('/api/users')
def get_user():
    username = request.args.get('username', '')

    query = "SELECT * FROM users WHERE username = '" + username + "'"
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'id': user[0],
            'username': user[1],
            'password': user[2] 
        })
    else:
        return jsonify({'error': 'User not found'}), 404
    
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000) 