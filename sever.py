
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

app = Flask(__name__)
# Render에서 제공하는 DATABASE_URL 환경 변수를 사용합니다.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    class_number = db.Column(db.Integer, nullable=False)
    student_number = db.Column(db.Integer, nullable=False)

    # 학년, 반, 번호가 고유해야 함을 나타내는 제약 조건 추가
    __table_args__ = (UniqueConstraint('grade', 'class_number', 'student_number', name='_grade_class_student_uc'),)

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    # 모든 필드가 있는지 확인
    required_fields = ['email', 'password', 'name', 'grade', 'class_number', 'student_number']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요.'}), 400

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    grade = data.get('grade')
    class_number = data.get('class_number')
    student_number = data.get('student_number')

    # 이메일 중복 확인
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '이미 사용중인 이메일입니다.'}), 409

    # 학생 중복 확인 (학년, 반, 번호)
    if User.query.filter_by(grade=grade, class_number=class_number, student_number=student_number).first():
        return jsonify({'error': '이미 등록된 학생입니다.'}), 409

    # 새 사용자 추가
    new_user = User(
        email=email,
        password=password, # 실제 앱에서는 비밀번호를 해싱하여 저장해야 합니다.
        name=name,
        grade=grade,
        class_number=class_number,
        student_number=student_number
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': '회원가입에 성공했습니다.'}), 201

# Render 환경에서는 gunicorn을 사용하므로 이 부분은 로컬 테스트용입니다.
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
