from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a strong secret in production

# --- Database Setup ---
def init_db():
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         username TEXT UNIQUE,
                         password TEXT)''')
        conn.commit()

init_db()

# --- Routes ---
@app.route('/')
def home():
    if 'user' in session:
        return render_template('index.html')
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        try:
            with sqlite3.connect('users.db') as conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            return redirect('/login')
        except sqlite3.IntegrityError:
            return "Username already exists"
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('users.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT password FROM users WHERE username=?", (username,))
            row = cur.fetchone()
            if row and check_password_hash(row[0], password):
                session['user'] = username
                return redirect('/')
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/generate-bill', methods=['POST'])
def generate_bill():
    client_name = request.form['client']
    email = request.form['email']
    items = request.form.getlist('item[]')
    prices = request.form.getlist('price[]')
    quantities = request.form.getlist('quantity[]')

    data = []
    total = 0
    for i in range(len(items)):
        subtotal = int(quantities[i]) * float(prices[i])
        total += subtotal
        data.append({
            'name': items[i],
            'price': prices[i],
            'qty': quantities[i],
            'subtotal': subtotal
        })

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Invoice")

    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"Client Name: {client_name}")
    p.drawString(50, height - 100, f"Email: {email}")

    y = height - 140
    p.drawString(50, y, "Item")
    p.drawString(200, y, "Price")
    p.drawString(300, y, "Quantity")
    p.drawString(400, y, "Subtotal")

    y -= 20
    for item in data:
        p.drawString(50, y, item['name'])
        p.drawString(200, y, str(item['price']))
        p.drawString(300, y, str(item['qty']))
        p.drawString(400, y, f"{item['subtotal']:.2f}")
        y -= 20

    p.drawString(300, y, "Total:")
    p.drawString(400, y, f"{total:.2f}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='invoice.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)