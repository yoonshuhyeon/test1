import os
import re
import requests
import jwt
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
from functools import wraps
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

app = Flask(__name__)
CORS(app)

# =================================
# CONFIGURATION
# =================================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key-for-dev')
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
    last_class_update = db.Column(db.DateTime, nullable=True)

class MealLike(db.Model):
    __tablename__ = 'meal_likes'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    meal_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('date', 'meal_type', 'user_id', name='_date_meal_user_uc'),)

class MealFeedback(db.Model):
    __tablename__ = 'meal_feedback'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    meal_type = db.Column(db.String(10), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    __table_args__ = (db.UniqueConstraint('date', 'meal_type', name='_date_meal_uc'),)

# =================================
# AUTHENTICATION DECORATORS
# =================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Token is missing or invalid!'}), 401
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def token_optional(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        current_user = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                current_user = User.query.get(data['user_id'])
            except Exception:
                pass
        return f(current_user, *args, **kwargs)
    return decorated

# =================================
# USER AUTHENTICATION ROUTES
# =================================
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data or not all(k in data for k in ['email', 'password', 'name', 'grade', 'class_number', 'student_number']):
        return jsonify({'error': '모든 필드를 입력해주세요.'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': '이미 사용중인 아이디입니다.'}), 409
    hashed_password = generate_password_hash(data['password'])
    new_user = User(email=data['email'], password=hashed_password, name=data['name'], grade=data['grade'], class_number=data['class_number'], student_number=data['student_number'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': '회원가입에 성공했습니다.'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': '아이디과 비밀번호를 입력해주세요.'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'error': '아이디 혹은 비밀번호가 틀렸습니다.'}), 401

    # Check if class info needs to be updated
    needs_update = False
    today = datetime.utcnow()
    march_first_this_year = datetime(today.year, 3, 1)

    if user.last_class_update is None:
        needs_update = True
    elif user.last_class_update < march_first_this_year:
        needs_update = True

    token = jwt.encode({'user_id': user.id, 'exp': datetime.utcnow() + timedelta(days=30)}, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({
        'message': '로그인 성공',
        'token': token,
        'user_name': user.name,
        'needs_class_info': needs_update
    }), 200

@app.route('/api/update-class', methods=['POST'])
@token_required
def update_class(current_user):
    data = request.get_json()
    if not data or not all(k in data for k in ['grade', 'class_number', 'student_number']):
        return jsonify({'error': '모든 필드를 입력해주세요.'}), 400

    current_user.grade = data['grade']
    current_user.class_number = data['class_number']
    current_user.student_number = data['student_number']
    current_user.last_class_update = datetime.utcnow()

    db.session.commit()

    return jsonify({'message': '반 정보가 성공적으로 업데이트되었습니다.'}), 200

# =================================
# QR CODE ROUTE
# =================================
@app.route('/api/generate_qr', methods=['GET'])
@token_required
def generate_qr(current_user):
    filename = f"{current_user.grade}_{current_user.class_number}_{current_user.student_number}.png"
    qr_url = f"https://raw.githubusercontent.com/yoonshuhyeon/test1/main/qr_codes/{filename}"
    return jsonify({"qr_code_url": qr_url})

# =================================
# NEIS API ROUTES
# =================================
NEIS_API_URL = "https://open.neis.go.kr/hub/"
MEAL_API_KEY = "368ccd7447b04140b197c937a072fb76"
ATPT_OFCDC_SC_CODE = "T10"
SD_SCHUL_CODE = "9290055"

@app.route('/api/meal', methods=['GET'])
@token_required
def get_meal(current_user):
    date_str = request.args.get('date', datetime.today().strftime("%Y%m%d"))
    params = {'KEY': MEAL_API_KEY, 'Type': 'json', 'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE, 'SD_SCHUL_CODE': SD_SCHUL_CODE, 'MLSV_YMD': date_str}
    try:
        response = requests.get(NEIS_API_URL + "mealServiceDietInfo", params=params)
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

@app.route('/api/timetable', methods=['GET'])
@token_required
def get_timetable(current_user):
    date_str = request.args.get('date', datetime.today().strftime("%Y%m%d"))
    params = {
        'KEY': MEAL_API_KEY, 'Type': 'json', 
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE, 
        'SD_SCHUL_CODE': SD_SCHUL_CODE, 
        'ALL_TI_YMD': date_str,
        'GRADE': str(current_user.grade),
        'CLASS_NM': str(current_user.class_number)
    }
    try:
        response = requests.get(NEIS_API_URL + "hisTimetable", params=params)
        response.raise_for_status()
        data = response.json()
        timetable_info = []
        service = data.get('hisTimetable')
        if service and len(service) > 1:
            timetable_info = service[1].get('row', [])
        return jsonify(timetable_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/nutrition', methods=['GET'])
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
        allergy_codes = set()

        for row in rows:
            if (v := row.get('ORPLC_INFO')): orplc_info.add(v)
            if (v := row.get('CAL_INFO')): cal_info.add(v)
            if (v := row.get('NTR_INFO')): ntr_info.add(v)
            if (dish_name := row.get('DDISH_NM')):
                found_codes = re.findall(r'\((\d+(?:\.\d+)*)\)', dish_name)
                for code_group in found_codes:
                    allergy_codes.update(c.strip() for c in code_group.split('.'))

        return jsonify({
            "ORPLC_INFO": ', '.join(sorted(orplc_info)) or '정보 없음',
            "CAL_INFO": ', '.join(sorted(cal_info)) or '정보 없음',
            "NTR_INFO": ', '.join(sorted(ntr_info)) or '정보 없음',
            "allergy": ','.join(sorted(list(allergy_codes))) or '정보 없음'
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =================================
# MEAL FEEDBACK & LIKE ROUTES
# =================================
@app.route('/api/submit_like', methods=['POST'])
@token_required
def submit_like(current_user):
    data = request.get_json()
    date = data.get('date', datetime.today().strftime("%Y%m%d"))
    meal_type = data.get('meal_type')
    if not meal_type:
        return jsonify({"error": "meal_type is required"}), 400
    existing_like = MealLike.query.filter_by(date=date, meal_type=meal_type, user_id=current_user.id).first()
    try:
        if existing_like:
            db.session.delete(existing_like)
            db.session.commit()
            return jsonify({"message": "좋아요를 취소했습니다."}), 200
        else:
            new_like = MealLike(date=date, meal_type=meal_type, user_id=current_user.id)
            db.session.add(new_like)
            db.session.commit()
            return jsonify({"message": "좋아요를 눌렀습니다."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_like_count', methods=['GET'])
@token_optional
def get_like_count(current_user):
    date = request.args.get('date', datetime.today().strftime("%Y%m%d"))
    meal_type = request.args.get('meal_type')
    if not meal_type:
        return jsonify({"error": "meal_type is required"}), 400
    count = MealLike.query.filter_by(date=date, meal_type=meal_type).count()
    user_has_liked = False
    if current_user:
        like = MealLike.query.filter_by(date=date, meal_type=meal_type, user_id=current_user.id).first()
        if like:
            user_has_liked = True
    return jsonify({"like_count": count, "user_has_liked": user_has_liked}), 200

# =================================
# APP INITIALIZATION
# =================================
@app.route('/')
def portal_home():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/login')
def portal_login():
    return send_from_directory(app.static_folder, 'login.html')

with app.app_context():
    db.create_all()
    try:
        with db.engine.begin() as connection:
            inspector = db.inspect(db.engine)
            if 'last_class_update' not in [col['name'] for col in inspector.get_columns('users')]:
                connection.execute(text('ALTER TABLE users ADD COLUMN last_class_update TIMESTAMP;'))
    except Exception as e:
        # Column already exists, which is fine.
        print(f"Could not add column: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
