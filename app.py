import sqlite3
from hashids import Hashids
from flask import Flask, render_template, request, flash, redirect, url_for, session
import qrcode
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from passlib.hash import pbkdf2_sha256
import os
from functools import wraps
import shortuuid



def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'mysecretkeyforurlsnipper!@#123'

login_manager = LoginManager()
login_manager.init_app(app)

hashids = Hashids(min_length=4, salt=app.config['SECRET_KEY'])

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

class User:
    def __init__(self, id, username):
        self.id = id
        self.username = username
        
    def is_active(self):
        # Return True if the user is considered active, False otherwise
        return True
    
    def get_id(self):
        # Return the unique identifier for the user as a string
        return str(self.id)
    
    def is_authenticated(self):
        # Return True if the user is authenticated, False otherwise
        return True

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM User WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1])
    return None

# @app.route('/<string:custom_url>')
# def redirect_to_url(custom_url):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     result = cursor.execute('SELECT original_url FROM urls WHERE custom_url = ?', (custom_url,)).fetchone()
#     short = cursor.execute('SELECT original_url FROM urls WHERE short_url = ?', (short_url,)).fetchone()

#     if result:
#         original_url = result
#         return redirect(original_url)
#     elif short:
#         return redirect(original_url)

#     else:
#         flash('Invalid URL')
#         return redirect(url_for('dashboard'))

@app.route('/', methods=('GET', 'POST'))
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, username, password FROM User WHERE username = ?', (username,))
        user = cursor.fetchone()

        conn.close()

        if user and pbkdf2_sha256.verify(password, user[2]):
            user_obj = User(user[0], user[1])
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html', error=None)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the username or email already exists in the database
        existing_user = cursor.execute('SELECT id FROM User WHERE username = ? OR email = ?', (username, email)).fetchone()

        if existing_user:
            flash('Username or email is already in use.')
            conn.close()
            return redirect(url_for('signup'))

        hashed_password = pbkdf2_sha256.hash(password)

        

        cursor.execute('INSERT INTO User (username, email, password) VALUES (?, ?, ?)', (username, email, hashed_password))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('signup.html', error='username/Email exists already ')

@app.route('/dashboard', methods=['GET', 'POST'])

def dashboard():
    user_id = current_user.id
    username = current_user.username
    
    conn = get_db_connection()

    if request.method == 'POST':
        url = request.form['url']
        custom = request.form['custom'] or None

        if not url:
            flash('The URL is required!')
            return redirect(url_for('dashboard'))

        if custom:
            # Check if the custom URL is already in use
            existing_url = conn.execute('SELECT id FROM urls WHERE custom_url = ?', (custom,)).fetchone()
            if existing_url:
                flash('The custom URL is already in use!')
                return redirect(url_for('dashboard'))

        url_data = conn.execute('INSERT INTO urls (original_url, custom_url, user_id) VALUES (?, ?, ?)',
                                (url, custom, user_id))

        url_id = url_data.lastrowid
        hashid = hashids.encode(url_id)

        if custom:
            short_url = request.host_url + custom
        else:
            short_url = request.host_url + hashid

        # Generate QR code
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(short_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Save the QR code image
        qr_code_filename = hashid + '.png'

        if custom:
            qr_code_filename = custom + '.png'

        qr_img.save(os.path.join('static', qr_code_filename))
        
        # Update the barcode_filename for the newly created URL
        conn.execute('UPDATE urls SET barcode_filename = ? WHERE id = ?', (qr_code_filename, url_id))
        conn.execute('UPDATE urls SET short_url = ? WHERE id = ?', (short_url, url_id))
        
        conn.commit()
        conn.close()

        return render_template('dashboard.html', short_url=short_url, qr_code_filename=qr_code_filename)

    return render_template('dashboard.html')



@app.route('/<id>')
def url_redirect(id):
    conn = get_db_connection()
    original_id = hashids.decode(id)
    
    if original_id:
        original_id = original_id[0]
        url_data = conn.execute('SELECT original_url, clicks FROM urls'
                                ' WHERE id = (?)', (original_id,)
                                ).fetchone()
        original_url = url_data['original_url']
        clicks = url_data['clicks']

        conn.execute('UPDATE urls SET clicks = ? WHERE id = ?',
                     (clicks+1, original_id))

        conn.commit()
        conn.close()
        return redirect(original_url)

    # If it's not a hashed URL, check for custom URL
    url_data = conn.execute('SELECT original_url, clicks FROM urls'
                            ' WHERE custom_url = ?', (id,)
                            ).fetchone()
    if url_data:
        original_url = url_data['original_url']
        clicks = url_data['clicks']

        conn.execute('UPDATE urls SET clicks = ? WHERE custom_url = ?',
                     (clicks + 1, id))

        conn.commit()
        conn.close()
        return redirect(original_url)

    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/stats')
def stats():
    user_id = current_user.id
    conn = get_db_connection()
    db_urls = conn.execute('SELECT id, created, barcode_filename, original_url, custom_url, clicks FROM urls WHERE user_id = ?', (user_id,)).fetchall()

    conn.close()

    count = 0
    urls = []
    for url in db_urls:
        url = dict(url)
        if url['custom_url']:
            url['short_url'] = request.host_url + url['custom_url']
        else:
            url['short_url'] = request.host_url + hashids.encode(url['id'])
        urls.append(url)

    return render_template('stats.html', urls=urls, count=count)

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

@app.route('/about')
def about():
    return render_template('about.html')

# Delete route
@app.route('/delete/<int:url_id>', methods=['POST', 'DELETE'])
def delete_url(url_id):
    user_id = current_user.id
    conn = get_db_connection()

    # Check if the URL with the specified id belongs to the current user
    url = conn.execute("SELECT * FROM urls WHERE id = ? AND user_id = ?", (url_id, user_id)).fetchone()

    if url is None:
        flash('Invalid URL or unauthorized access')
        return redirect(url_for('dashboard'))

    # Delete the URL from the database
    conn.execute("DELETE FROM urls WHERE id = ?", (url_id,))
    conn.commit()
    conn.close()

    flash('URL successfully deleted')
    return redirect(url_for('stats'))


if __name__ == "__main__":
    app.run()