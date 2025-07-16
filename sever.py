import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)  # 해시된 비밀번호를 저장하기 위해 길이를 늘립니다.
    name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    class_number = db.Column(db.Integer, nullable=False)
    student_number = db.Column(db.Integer, nullable=False)

    __table_args__ = (UniqueConstraint('grade', 'class_number', 'student_number', name='_grade_class_student_uc'),)

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    required_fields = ['email', 'password', 'name', 'grade', 'class_number', 'student_number']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요.'}), 400

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    grade = data.get('grade')
    class_number = data.get('class_number')
    student_number = data.get('student_number')

    if User.query.filter_by(email=email).first():
        return jsonify({'error': '이미 사용중인 이메일입니다.'}), 409

    if User.query.filter_by(grade=grade, class_number=class_number, student_number=student_number).first():
        return jsonify({'error': '이미 등록된 학생입니다.'}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(
        email=email,
        password=hashed_password,
        name=name,
        grade=grade,
        class_number=class_number,
        student_number=student_number
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': '회원가입에 성공했습니다.'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': '이메일과 비밀번호를 입력해주세요.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': '이메일 또는 비밀번호가 잘못되었습니다.'}), 401

    return jsonify({'message': '로그인 성공'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
