from flask import Flask, render_template, request, redirect, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import os
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt','mp4'}
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///task.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
db = SQLAlchemy(app)
IST = timezone(timedelta(hours=5, minutes=30))
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    tasks = db.relationship('Task', backref='user', lazy=True)
class Task(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(300))
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(IST).replace(microsecond=0))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'warning')
            return redirect('/signup')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Account created. Please login.', 'success')
        return redirect('/login')
    return render_template('signup.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Logged in successfully.', 'success')
            return redirect('/')
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.', 'info')
    return redirect('/login')
@app.route('/', methods=["GET", "POST"])
def home():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files.get('file')
        file_name = None
        if file and allowed_file(file.filename):
            file_name = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
        task = Task(title=title, description=description, file_name=file_name, user_id=user_id)
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully!', 'success')
    query = request.args.get('query')
    if query:
        alltask = Task.query.filter_by(user_id=user_id).filter(
            Task.title.ilike(f'%{query}%') | Task.description.ilike(f'%{query}%')
        ).all()
    else:
        alltask = Task.query.filter_by(user_id=user_id).all()
    return render_template('index.html', alltask=alltask)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/delete/<int:sno>')
def delete(sno):
    if 'user_id' not in session:
        return redirect('/login')
    task = Task.query.get_or_404(sno)
    if task.user_id != session['user_id']:
        return "Unauthorized", 403
    db.session.delete(task)
    db.session.commit()
    flash('Item deleted.', 'success')
    return redirect('/')
@app.route('/update/<int:sno>', methods=["GET", "POST"])
def update(sno):
    if 'user_id' not in session:
        return redirect('/login')
    task = Task.query.get_or_404(sno)
    if task.user_id != session['user_id']:
        return "Unauthorized", 403
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        db.session.commit()
        flash('Task updated.', 'info')
        return redirect('/')
    return render_template('update.html', task=task)
@app.route("/attach_file/<int:sno>", methods=["POST"])
def attach_file(sno):
    if 'user_id' not in session:
        return redirect('/login')
    task = Task.query.get_or_404(sno)
    if task.user_id != session['user_id']:
        return "Unauthorized", 403
    file = request.files.get("file")
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        task.file_name = filename
        db.session.commit()
        flash("File attached successfully!", "success")
    else:
        flash("Invalid file or no file selected.", "warning")
    return redirect("/")
@app.route("/instructions")
def instructions():
    return render_template("instructions.html")
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=10000)