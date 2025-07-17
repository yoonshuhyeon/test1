import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# =================================
# DATABASE CONFIGURATION
# =================================
# Render의 DATABASE_URL을 사용하고, postgresql dialect에 맞게 수정
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =================================
# DATABASE MODELS
# =================================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    class_number = db.Column(db.Integer, nullable=False)
    student_number = db.Column(db.Integer, nullable=False)

class MealFeedback(db.Model):
    __tablename__ = 'meal_feedback'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False) # "YYYYMMDD"
    meal_type = db.Column(db.String(10), nullable=False) # "lunch", "dinner"
    rating = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    likes = db.Column(db.Integer, default=0)
    # 날짜와 식사 종류별로 하나의 피드백만 존재하도록 설정
    __table_args__ = (db.UniqueConstraint('date', 'meal_type', name='_date_meal_uc'),)


# =================================
# USER AUTHENTICATION ROUTES
# =================================
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    required_fields = ['email', 'password', 'name', 'grade', 'class_number', 'student_number']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요.'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': '이미 사용중인 이메일입니다.'}), 409

    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        email=data['email'],
        password=hashed_password,
        name=data['name'],
        grade=data['grade'],
        class_number=data['class_number'],
        student_number=data['student_number']
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': '회원가입에 성공했습니다.'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': '이메일과 비밀번호를 입력해주세요.'}), 400

    user = User.query.filter_by(email=data['email']).first()

    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'error': '아이디 혹은 비밀번호가 틀렸습니다.'}), 401

    return jsonify({'message': '로그인 성공'}), 200

# =================================
# QR CODE ROUTE
# =================================
def github_qr_url(filename):
    return f"https://raw.githubusercontent.com/yoonshuhyeon/test1/main/qr_codes/{filename}"

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    grade = str(data.get('grade', '')).strip()
    class_num = str(data.get('class_num', '')).strip()
    student_num = str(data.get('student_num', '')).strip()
    
    if not grade or not class_num or not student_num:
        return jsonify({"error": "grade, class_num, student_num are required"}), 400

    filename = f"{grade}_{class_num}_{student_num}.png"
    qr_url = github_qr_url(filename)
    return jsonify({"qr_code_url": qr_url})

# =================================
# NEIS MEAL API ROUTES
# =================================
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
MEAL_API_KEY = "368ccd7447b04140b197c937a072fb76"
ATPT_OFCDC_SC_CODE = "T10"
SD_SCHUL_CODE = "9290055"

@app.route('/meal', methods=['GET'])
def get_meal():
    date_str = request.args.get('date', datetime.today().strftime("%Y%m%d"))
    params = {
        'KEY': MEAL_API_KEY, 'Type': 'json',
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE,
        'SD_SCHUL_CODE': SD_SCHUL_CODE, 'MLSV_YMD': date_str
    }
    try:
        response = requests.get(MEAL_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        meal_info = {'lunch': '정보 없음', 'dinner': '정보 없음'}
        service = data.get('mealServiceDietInfo')
        if service and len(service) > 1:
            rows = service[1].get('row', [])
            for meal in rows:
                if meal.get('MMEAL_SC_NM') == '중식':
                    meal_info['lunch'] = meal.get('DDISH_NM', '정보 없음').replace('<br/>', '\n')
                elif meal.get('MMEAL_SC_NM') == '석식':
                    meal_info['dinner'] = meal.get('DDISH_NM', '정보 없음').replace('<br/>', '\n')
        else:
            meal_info['error'] = "급식 정보가 없습니다."
        return jsonify(meal_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/nutrition', methods=['GET'])
def get_nutrition():
    date_str = request.args.get('date', datetime.today().strftime("%Y%m%d"))
    params = {
        'KEY': MEAL_API_KEY, 'Type': 'json',
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE,
        'SD_SCHUL_CODE': SD_SCHUL_CODE, 'MLSV_YMD': date_str
    }
    try:
        response = requests.get(MEAL_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        service = data.get('mealServiceDietInfo')
        if not service or len(service) < 2:
            return jsonify({"error": "급식 정보가 없습니다."}), 404
        
        rows = service[1].get('row', [])
        orplc_info = set()
        cal_info = set()
        ntr_info = set()
        for row in rows:
            if (v := row.get('ORPLC_INFO')): orplc_info.add(v)
            if (v := row.get('CAL_INFO')): cal_info.add(v)
            if (v := row.get('NTR_INFO')): ntr_info.add(v)

        return jsonify({
            "ORPLC_INFO": ', '.join(sorted(orplc_info)) or '정보 없음',
            "CAL_INFO": ', '.join(sorted(cal_info)) or '정보 없음',
            "NTR_INFO": ', '.join(sorted(ntr_info)) or '정보 없음',
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =================================
# MEAL FEEDBACK ROUTES
# =================================
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    date = data.get('date', datetime.today().strftime("%Y%m%d"))
    meal_type = data.get('meal_type')
    rating = data.get('rating')
    feedback_text = data.get('feedback')

    if not all([meal_type, rating]):
        return jsonify({"error": "date, meal_type, rating are required"}), 400
    
    try:
        feedback_entry = MealFeedback.query.filter_by(date=date, meal_type=meal_type).first()
        if not feedback_entry:
            feedback_entry = MealFeedback(date=date, meal_type=meal_type, rating=0)
            db.session.add(feedback_entry)

        feedback_entry.rating = int(rating)
        feedback_entry.feedback = feedback_text
        db.session.commit()
        return jsonify({"message": "피드백 제출 완료"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/submit_like', methods=['POST'])
def submit_like():
    data = request.get_json()
    date = data.get('date', datetime.today().strftime("%Y%m%d"))
    meal_type = data.get('meal_type')

    if not meal_type:
        return jsonify({"error": "meal_type is required"}), 400

    try:
        feedback_entry = MealFeedback.query.filter_by(date=date, meal_type=meal_type).first()
        if not feedback_entry:
            feedback_entry = MealFeedback(date=date, meal_type=meal_type, rating=3, likes=1)
            db.session.add(feedback_entry)
        else:
            feedback_entry.likes = (feedback_entry.likes or 0) + 1
        
        db.session.commit()
        return jsonify({"message": "좋아요 처리 완료"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/get_like_count', methods=['GET'])
def get_like_count():
    date = request.args.get('date', datetime.today().strftime("%Y%m%d"))
    meal_type = request.args.get('meal_type')

    if not meal_type:
        return jsonify({"error": "meal_type is required"}), 400

    feedback_entry = MealFeedback.query.filter_by(date=date, meal_type=meal_type).first()
    
    if feedback_entry:
        return jsonify({"like_count": feedback_entry.likes or 0}), 200
    else:
        return jsonify({"like_count": 0}), 200

# =================================
# APP INITIALIZATION
# =================================
@app.route('/')
def index():
    return jsonify({"message": "server ok"})

# 앱 시작 시 데이터베이스 테이블 자동 생성
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
