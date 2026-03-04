"""
2SOUL Shop - Backend
Flask + SQLite + Admin Panel
Поддержка нескольких фото, описания товаров, СДЭК
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import sqlite3
import os
import uuid
import json

app = Flask(__name__)
app.secret_key = 'change-this-secret-key-2soul-shop'  # ПОМЕНЯЙ!
CORS(app)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB

# Путь к базе данных — /data для Amvera (persistentMount)
DATA_DIR = '/data' if os.path.exists('/data') else '.'
DB_PATH = os.path.join(DATA_DIR, 'shop.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)


# ==================== DATABASE ====================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            price INTEGER NOT NULL,
            description TEXT,
            images TEXT DEFAULT '[]',
            sizes TEXT DEFAULT '["S","M","L","XL"]',
            tag TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            customer_telegram TEXT,
            customer_vk TEXT,
            customer_city TEXT,
            cdek_point TEXT,
            customer_comment TEXT,
            items TEXT,
            total INTEGER,
            status TEXT DEFAULT 'new',
            telegram_user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Добавляем новые колонки если их нет (для миграции)
    # Добавляем новые колонки если их нет (для миграции)
    try:
        cursor.execute('ALTER TABLE products ADD COLUMN description TEXT')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE products ADD COLUMN images TEXT DEFAULT "[]"')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN customer_telegram TEXT')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN customer_vk TEXT')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN cdek_point TEXT')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT "sbp"')
    except:
        pass
    # Админ по умолчанию
    try:
        cursor.execute(
            'INSERT INTO admins (username, password) VALUES (?, ?)',
            ('admin', generate_password_hash('admin123'))
        )
    except sqlite3.IntegrityError:
        pass
    
    # Категории
    default_categories = [
        ('Худи', 'hoodies'),
        ('Футболки', 'tshirts'),
        ('Штаны', 'pants'),
        ('Куртки', 'jackets'),
        ('Аксессуары', 'accessories')
    ]
    
    for name, slug in default_categories:
        try:
            cursor.execute('INSERT INTO categories (name, slug) VALUES (?, ?)', (name, slug))
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()


# ==================== HELPERS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def save_uploaded_file(file):
    """Сохраняет файл и возвращает путь"""
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return f"/static/uploads/{filename}"
    return None


# ==================== API ====================

@app.route('/api/products')
def api_products():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, c.name as category_name, c.slug as category_slug
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.active = 1
        ORDER BY p.created_at DESC
    ''')
    
    products = []
    for row in cursor.fetchall():
        # Парсим images
        images = []
        try:
            images = json.loads(row['images']) if row['images'] else []
        except:
            if row['images']:
                images = [row['images']]
        
        # Для обратной совместимости
        main_image = images[0] if images else None
        
        products.append({
            'id': row['id'],
            'name': row['name'],
            'category': row['category_slug'] or 'other',
            'category_name': row['category_name'] or 'Другое',
            'price': row['price'],
            'description': row['description'] or '',
            'image': main_image,
            'images': images,
            'sizes': json.loads(row['sizes']) if row['sizes'] else ['S', 'M', 'L', 'XL'],
            'tag': row['tag']
        })
    
    conn.close()
    return jsonify(products)


@app.route('/api/categories')
def api_categories():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY id')
    categories = [{'id': row['id'], 'name': row['name'], 'slug': row['slug']} 
                  for row in cursor.fetchall()]
    conn.close()
    return jsonify(categories)


@app.route('/api/orders', methods=['POST'])
def api_create_order():
    data = request.json
    customer = data.get('customer', {})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO orders (
            customer_name, customer_phone, customer_telegram, customer_vk,
            customer_city, cdek_point, customer_comment, 
            items, total, payment_method, telegram_user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        customer.get('name'),
        customer.get('phone'),
        customer.get('telegram'),
        customer.get('vk'),
        customer.get('city'),
        json.dumps(customer.get('cdek_point'), ensure_ascii=False) if customer.get('cdek_point') else None,
        customer.get('comment'),
        json.dumps(data.get('items', []), ensure_ascii=False),
        data.get('total', 0),
        data.get('payment_method', 'sbp'),
        data.get('telegram_user_id')
    ))
    
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'order_id': order_id})


# ==================== ADMIN ====================

@app.route('/admin')
def admin_index():
    if 'admin_id' in session:
        return redirect(url_for('admin_products'))
    return redirect(url_for('admin_login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
        admin = cursor.fetchone()
        conn.close()
        
        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['id']
            return redirect(url_for('admin_products'))
        else:
            error = 'Неверный логин или пароль'
    
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/products')
@login_required
def admin_products():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.created_at DESC
    ''')
    products = cursor.fetchall()
    
    cursor.execute('SELECT * FROM categories ORDER BY id')
    categories = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_products.html', products=products, categories=categories)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY id')
    categories = cursor.fetchall()
    
    if request.method == 'POST':
        name = request.form.get('name')
        category_id = request.form.get('category_id')
        price = request.form.get('price')
        description = request.form.get('description', '')
        sizes = request.form.getlist('sizes')
        tag = request.form.get('tag') or None
        
        # Обработка нескольких фото
        images = []
        files = request.files.getlist('images')
        for file in files:
            path = save_uploaded_file(file)
            if path:
                images.append(path)
        
        cursor.execute('''
            INSERT INTO products (name, category_id, price, description, images, sizes, tag)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, category_id, price, description, json.dumps(images), json.dumps(sizes), tag))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_products'))
    
    conn.close()
    return render_template('admin_product_form.html', categories=categories, product=None)


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        conn.close()
        return redirect(url_for('admin_products'))
    
    cursor.execute('SELECT * FROM categories ORDER BY id')
    categories = cursor.fetchall()
    
    if request.method == 'POST':
        name = request.form.get('name')
        category_id = request.form.get('category_id')
        price = request.form.get('price')
        description = request.form.get('description', '')
        sizes = request.form.getlist('sizes')
        tag = request.form.get('tag') or None
        active = 1 if request.form.get('active') else 0
        
        # Текущие изображения
        try:
            current_images = json.loads(product['images']) if product['images'] else []
        except:
            current_images = []
        
        # Удаляемые изображения
        remove_images = request.form.getlist('remove_images')
        for img_path in remove_images:
            if img_path in current_images:
                current_images.remove(img_path)
                # Удаляем файл
                try:
                    file_path = img_path.replace('/static/uploads/', '')
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file_path))
                except:
                    pass
        
        # Новые изображения
        files = request.files.getlist('images')
        for file in files:
            path = save_uploaded_file(file)
            if path:
                current_images.append(path)
        
        cursor.execute('''
            UPDATE products 
            SET name=?, category_id=?, price=?, description=?, images=?, sizes=?, tag=?, active=?
            WHERE id=?
        ''', (name, category_id, price, description, json.dumps(current_images), json.dumps(sizes), tag, active, product_id))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_products'))
    
    conn.close()
    return render_template('admin_product_form.html', categories=categories, product=product)


@app.route('/admin/products/delete/<int:product_id>')
@login_required
def admin_delete_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT images FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if product and product['images']:
        try:
            images = json.loads(product['images'])
            for img_path in images:
                try:
                    file_path = img_path.replace('/static/uploads/', '')
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file_path))
                except:
                    pass
        except:
            pass
    
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
@login_required
def admin_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
    orders = cursor.fetchall()
    conn.close()
    
    return render_template('admin_orders.html', orders=orders)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
def admin_update_order_status(order_id):
    status = request.form.get('status')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_orders'))


@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        slug = request.form.get('slug')
        
        try:
            cursor.execute('INSERT INTO categories (name, slug) VALUES (?, ?)', (name, slug))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
    
    cursor.execute('SELECT * FROM categories ORDER BY id')
    categories = cursor.fetchall()
    conn.close()
    
    return render_template('admin_categories.html', categories=categories)


@app.route('/admin/categories/delete/<int:category_id>')
@login_required
def admin_delete_category(category_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_categories'))


@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    message = None
    error = None
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admins WHERE id = ?', (session['admin_id'],))
        admin = cursor.fetchone()
        
        if not check_password_hash(admin['password'], current_password):
            error = 'Неверный текущий пароль'
        elif new_password != confirm_password:
            error = 'Пароли не совпадают'
        elif len(new_password) < 6:
            error = 'Пароль должен быть минимум 6 символов'
        else:
            cursor.execute(
                'UPDATE admins SET password = ? WHERE id = ?',
                (generate_password_hash(new_password), session['admin_id'])
            )
            conn.commit()
            message = 'Пароль успешно изменён'
        
        conn.close()
    
    return render_template('admin_settings.html', message=message, error=error)


# ==================== STATIC ====================

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# Инициализация БД при запуске
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
