# app.py
# Main Flask app untuk CMS Mini dengan fitur modern

import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.sql import func

# Inisialisasi Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cmsmini.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Inisialisasi database dan login manager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Silakan login terlebih dahulu untuk mengakses halaman ini.'
login_manager.login_message_category = 'warning'

# Model User dengan metode helper untuk pengecekan role
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # admin/editor
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_editor(self):
        return self.role == 'editor'
    
    def can_edit_post(self, post):
        return self.is_admin() or post.author_id == self.id
    
    def can_delete_post(self, post):
        return self.is_admin() or post.author_id == self.id

# Model Post dengan tambahan field untuk aksesibilitas dan tracking
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(200))
    image_alt_text = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def format_date(date):
    return date.strftime('%d %b %Y %H:%M')

# Context processor untuk template
@app.context_processor
def utility_processor():
    return {
        'format_date': format_date,
        'now': datetime.utcnow()
    }

# Loader untuk Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_message='Halaman yang Anda cari tidak ditemukan.'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', error_code=403, error_message='Anda tidak memiliki izin untuk mengakses halaman ini.'), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_code=500, error_message='Terjadi kesalahan pada server. Silakan coba lagi nanti.'), 500

# Route untuk serve file upload
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            error = 'Username dan password harus diisi'
        else:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('Login berhasil! Selamat datang, {}.'.format(user.username), 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                error = 'Username atau password salah'
    
    return render_template('login.html', error=error)

# Route logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout berhasil!', 'success')
    return redirect(url_for('login'))

# Dashboard utama
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    # Admin bisa lihat semua post, editor hanya post miliknya
    if current_user.is_admin():
        posts = Post.query.order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.filter_by(author_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('dashboard.html', posts=posts)

# Route untuk melihat post
@app.route('/post/<int:post_id>')
@login_required
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    # Cek apakah user punya akses untuk melihat post
    if not current_user.is_admin() and post.author_id != current_user.id:
        abort(403)
    
    can_edit = current_user.can_edit_post(post)
    can_delete = current_user.can_delete_post(post)
    
    return render_template('post_detail.html', post=post, can_edit=can_edit, can_delete=can_delete)

# Route untuk membuat post
@app.route('/post/create', methods=['GET', 'POST'])
@login_required
def create_post():
    form_data = {}
    errors = {}
    
    if request.method == 'POST':
        # Ambil data dari form
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        image = request.files.get('image')
        image_alt_text = request.form.get('image_alt_text', '').strip()
        
        form_data = {
            'title': title,
            'content': content,
            'image_alt_text': image_alt_text
        }
        
        # Validasi input
        if not title:
            errors['title'] = 'Judul tidak boleh kosong'
        
        if not content:
            errors['content'] = 'Konten tidak boleh kosong'
        
        # Validasi gambar jika ada
        filename = None
        if image and image.filename:
            if not allowed_file(image.filename):
                errors['image'] = 'Format file tidak didukung. Gunakan PNG, JPG, JPEG, atau GIF'
            else:
                # Generate nama file unik untuk mencegah overwrite
                ext = image.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                
                # Validasi alt text hanya jika ada gambar
                if not image_alt_text:
                    errors['image_alt_text'] = 'Alt text diperlukan untuk aksesibilitas gambar'
        
        # Jika tidak ada error, simpan post
        if not errors:
            try:
                # Simpan gambar jika ada
                if filename:
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                # Buat post baru
                post = Post(
                    title=title,
                    content=content,
                    image_filename=filename,
                    image_alt_text=image_alt_text,
                    author_id=current_user.id
                )
                
                db.session.add(post)
                db.session.commit()
                
                flash('Post berhasil dibuat!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f'Terjadi kesalahan: {str(e)}', 'danger')
    
    return render_template('post_form.html', is_edit=False, form_data=form_data, errors=errors)

# Route untuk edit post
@app.route('/post/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Cek apakah user punya akses untuk edit
    if not current_user.can_edit_post(post):
        flash('Anda tidak memiliki izin untuk mengedit post ini!', 'danger')
        return redirect(url_for('dashboard'))
    
    form_data = {}
    errors = {}
    
    if request.method == 'POST':
        # Ambil data dari form
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        image = request.files.get('image')
        image_alt_text = request.form.get('image_alt_text', '').strip()
        
        form_data = {
            'title': title,
            'content': content,
            'image_alt_text': image_alt_text
        }
        
        # Validasi input
        if not title:
            errors['title'] = 'Judul tidak boleh kosong'
        
        if not content:
            errors['content'] = 'Konten tidak boleh kosong'
        
        # Validasi alt text jika sudah ada gambar
        if post.image_filename and not image_alt_text:
            errors['image_alt_text'] = 'Alt text diperlukan untuk aksesibilitas gambar'
        
        # Validasi gambar baru jika ada
        if image and image.filename:
            if not allowed_file(image.filename):
                errors['image'] = 'Format file tidak didukung. Gunakan PNG, JPG, JPEG, atau GIF'
            elif not image_alt_text:
                errors['image_alt_text'] = 'Alt text diperlukan untuk aksesibilitas gambar'
        
        # Jika tidak ada error, update post
        if not errors:
            try:
                # Update data post
                post.title = title
                post.content = content
                post.image_alt_text = image_alt_text
                
                # Simpan gambar baru jika ada
                if image and image.filename:
                    ext = image.filename.rsplit('.', 1)[1].lower()
                    filename = f"{uuid.uuid4().hex}.{ext}"
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    
                    # Hapus gambar lama jika ada
                    if post.image_filename:
                        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    post.image_filename = filename
                
                db.session.commit()
                
                flash('Post berhasil diperbarui!', 'success')
                return redirect(url_for('view_post', post_id=post.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Terjadi kesalahan: {str(e)}', 'danger')
    else:
        # Isi form dengan data post yang sudah ada
        form_data = {
            'title': post.title,
            'content': post.content,
            'image_alt_text': post.image_alt_text or ''
        }
    
    return render_template('post_form.html', is_edit=True, post=post, form_data=form_data, errors=errors)

# Route untuk hapus post
@app.route('/post/delete/<int:post_id>', methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Cek apakah user punya akses untuk hapus
    if not current_user.can_delete_post(post):
        flash('Anda tidak memiliki izin untuk menghapus post ini!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Hapus gambar jika ada
            if post.image_filename:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename)
                if os.path.exists(image_path):
                    os.remove(image_path)
            
            # Hapus post dari database
            db.session.delete(post)
            db.session.commit()
            
            flash('Post berhasil dihapus!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

# Fungsi untuk inisialisasi database dan membuat user awal
def create_tables():
    with app.app_context():
        db.create_all()
        # Buat user admin dan editor default jika belum ada
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
        if not User.query.filter_by(username='editor').first():
            editor = User(username='editor', role='editor')
            editor.set_password('editor123')
            db.session.add(editor)
        db.session.commit()

# Inisialisasi database akan dilakukan saat aplikasi dijalankan

if __name__ == '__main__':
    # Pastikan folder uploads ada
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Inisialisasi database
    with app.app_context():
        create_tables()
    app.run(debug=True)
