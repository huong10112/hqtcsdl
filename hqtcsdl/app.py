import pyodbc
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Cấu hình kết nối với SQL Server
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://sa:030303006302@localhost/QlyTinTuc?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key'  # Thêm secret key cho session

db = SQLAlchemy(app)

# Kết nối thủ công bằng pyodbc (nếu không dùng SQLAlchemy)
def get_db_connection():
    conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
                          'SERVER=localhost;'
                          'DATABASE=QlyTinTuc;'
                          'UID=sa;'
                          'PWD=030303006302')
    return conn

# Trang chủ hiển thị các bài viết đã duyệt
@app.route('/')
def index():
    # Kiểm tra nếu người dùng đã đăng nhập
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Nếu chưa đăng nhập, chuyển hướng đến trang đăng nhập

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Lấy tất cả các bài viết đã được duyệt (DuyetBaiViet = 1)
    cursor.execute("SELECT * FROM BAIVIET WHERE DuyetBaiViet = 1")
    articles = cursor.fetchall()

    conn.close()

    # Kiểm tra vai trò của người dùng để quyết định có hiển thị bài viết hay không
    if session['role'] == 'ADMIN' or session['role'] == 'VIEWER':
        return render_template('index.html', articles=articles)  # Hiển thị danh sách bài viết
    else:
        return 'Bạn không có quyền truy cập vào bài viết.'  # Nếu không phải ADMIN hay VIEWER, hiển thị thông báo

def create_user(username, password, email, role):
    # Kết nối cơ sở dữ liệu và lưu người dùng với mật khẩu gốc
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO NGUOIDUNG (TenDangNhap, MatKhau, Email, VaiTro) VALUES (?, ?, ?, ?)", 
                   (username, password, email, role))
    conn.commit()
    conn.close()


# Đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM NGUOIDUNG WHERE TenDangNhap = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        # In ra tên đăng nhập và mật khẩu người dùng nhập vào
        print(f'Username: {username}, Password: {password}')
        # In ra thông tin người dùng từ DB và mật khẩu đã lưu
        if user:
            print(f'User from DB: {user[1]}, Stored Password: {user[2]}')

        # So sánh mật khẩu nhập vào với mật khẩu trong DB
        if user and user[2] == password:  # Kiểm tra mật khẩu
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            return redirect(url_for('index'))
        else:
            return 'Sai tên đăng nhập hoặc mật khẩu'
    
    return render_template('login.html')

# Đăng xuất
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

# Tạo bài viết mới
@app.route('/create_article', methods=['GET', 'POST'])
def create_article():
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form['category_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO BAIVIET (TieuDe, NoiDung, MaTacGia, MaDanhMuc) VALUES (?, ?, ?, ?)", 
                       (title, content, session['user_id'], category_id))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM DANHMUC")
    categories = cursor.fetchall()
    conn.close()

    return render_template('create_article.html', categories=categories)

# Xem chi tiết bài viết và bình luận
@app.route('/article/<int:article_id>', methods=['GET', 'POST'])
def article(article_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BAIVIET WHERE MaBaiViet = ?", (article_id,))
    article = cursor.fetchone()

    cursor.execute("SELECT * FROM BINHLUAN WHERE MaBaiViet = ?", (article_id,))
    comments = cursor.fetchall()
    conn.close()

    if request.method == 'POST':
        comment_content = request.form['comment']
        if 'user_id' in session:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO BINHLUAN (MaBaiViet, MaNguoiDung, NoiDung) VALUES (?, ?, ?)",
                           (article_id, session['user_id'], comment_content))
            conn.commit()
            conn.close()

            return redirect(url_for('article', article_id=article_id))

    return render_template('article.html', article=article, comments=comments)

if __name__ == '__main__':
    app.run(debug=True)
