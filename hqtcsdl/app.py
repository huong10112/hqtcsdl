# Import necessary libraries and modules
import pyodbc
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Cấu hình kết nối với SQL Server
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://sa:030303006302@localhost/QlyTinTuc?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key'  # Thêm secret key cho session

# Kết nối cơ sở dữ liệu
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

        if user and user[2] == password:  # Kiểm tra mật khẩu
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            return redirect(url_for('index'))
        else:
            flash("Sai tên đăng nhập hoặc mật khẩu")

    return render_template('login.html')

# Đăng xuất
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

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

        flash("Bài viết đã được tạo thành công!")
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM DANHMUC")
    categories = cursor.fetchall()
    conn.close()

    return render_template('create_article.html', categories=categories)

# Sửa bài viết
@app.route('/edit_article/<int:article_id>', methods=['GET', 'POST'])
def edit_article(article_id):
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BAIVIET WHERE MaBaiViet = ?", (article_id,))
    article = cursor.fetchone()

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form['category_id']
        
        cursor.execute("UPDATE BAIVIET SET TieuDe = ?, NoiDung = ?, MaDanhMuc = ? WHERE MaBaiViet = ?", 
                       (title, content, category_id, article_id))
        conn.commit()
        conn.close()
        
        flash("Bài viết đã được cập nhật thành công!")
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM DANHMUC")
    categories = cursor.fetchall()
    conn.close()

    return render_template('edit_article.html', article=article, categories=categories)

# Xóa bài viết
@app.route('/delete_article/<int:article_id>', methods=['POST'])
def delete_article(article_id):
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM BAIVIET WHERE MaBaiViet = ?", (article_id,))
    conn.commit()
    conn.close()

    flash("Bài viết đã được xóa thành công!")
    return redirect(url_for('index'))

# Route hiển thị bài viết theo từ khóa
@app.route('/keyword/<string:keyword_name>')
def keyword_articles(keyword_name):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Lấy các bài viết có từ khóa được chọn
    cursor.execute("""
        SELECT A.MaBaiViet, A.TieuDe
        FROM BAIVIET A
        JOIN BV_THE BV ON A.MaBaiViet = BV.MaBaiViet
        JOIN THE T ON BV.MaThe = T.MaThe
        WHERE T.TenThe = ?
    """, (keyword_name,))
    articles = cursor.fetchall()
    
    conn.close()

    # Nếu không có bài viết nào với từ khóa đó
    if not articles:
        return f"Không có bài viết nào với từ khóa '{keyword_name}'."

    return render_template('keyword_articles.html', articles=articles, keyword_name=keyword_name)

if __name__ == "__main__":
    app.run(debug=True)
