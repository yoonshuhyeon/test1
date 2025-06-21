import os
import requests
import psycopg2-binary
from urllib.parse import urlparse
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Heroku에선 환경변수로부터 DB URL을 받음
DATABASE_URL = os.environ.get("DATABASE_URL")

# QR 코드 저장 경로 설정
if DATABASE_URL:
    QR_FOLDER = "/tmp/qr_codes"  # Heroku에선 임시 디렉토리
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    QR_FOLDER = os.path.join(BASE_DIR, "qr_codes")
os.makedirs(QR_FOLDER, exist_ok=True)

# DB 연결 함수
def get_connection():
    if DATABASE_URL:
        result = urlparse(DATABASE_URL)
        return psycopg2.connect(
            dbname=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
    else:
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback.db")
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

# DB 초기화
def init_feedback_db():
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_feedback (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                rating INTEGER NOT NULL,
                feedback TEXT,
                likes INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                rating INTEGER NOT NULL,
                feedback TEXT,
                likes INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    cursor.close()
    conn.close()

init_feedback_db()

# 급식 API 관련 정보
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
MEAL_API_KEY = "368ccd7447b04140b197c937a072fb76"
ATPT_OFCDC_SC_CODE = "T10"
SD_SCHUL_CODE = "9290055"

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    grade = str(data.get('grade', '')).strip()
    class_num = str(data.get('class_num', '')).strip()
    student_num = str(data.get('student_num', '')).strip()
    name = str(data.get('name', '')).strip()
    filename = f"{grade}_{class_num}_{student_num}.png"
    filepath = os.path.join(QR_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "해당 학생의 QR 코드가 존재하지 않습니다."}), 404
    return jsonify({"qr_code_path": filename})

@app.route('/qr_codes/<path:filename>')
def serve_qr_code(filename):
    return send_from_directory(QR_FOLDER, filename)

@app.route('/meal', methods=['GET'])
def get_meal():
    date_str = request.args.get('date', datetime.today().strftime("%Y%m%d"))
    params = {
        'KEY': MEAL_API_KEY,
        'Type': 'json',
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE,
        'SD_SCHUL_CODE': SD_SCHUL_CODE,
        'MLSV_YMD': date_str
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
                t = meal.get('MMEAL_SC_NM', '')
                d = meal.get('DDISH_NM', '')
                if t == '중식':
                    meal_info['lunch'] = d
                elif t == '석식':
                    meal_info['dinner'] = d
        else:
            meal_info['error'] = "급식 정보가 없습니다."
        return jsonify(meal_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/nutrition', methods=['GET'])
def get_nutrition():
    date_str = request.args.get('date', datetime.today().strftime("%Y%m%d"))
    params = {
        'KEY': MEAL_API_KEY,
        'Type': 'json',
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE,
        'SD_SCHUL_CODE': SD_SCHUL_CODE,
        'MLSV_YMD': date_str
    }
    try:
        response = requests.get(MEAL_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        service = data.get('mealServiceDietInfo')
        if not service or len(service) < 2:
            return jsonify({"error": "급식 정보가 없습니다."}), 404
        rows = service[1].get('row', [])
        orplc_info, cal_info, ntr_info, menu_names, allergy_codes = [], [], [], [], []
        for row in rows:
            if (v := row.get('ORPLC_INFO')): orplc_info.append(v)
            if (v := row.get('CAL_INFO')): cal_info.append(v)
            if (v := row.get('NTR_INFO')): ntr_info.append(v)
            if (v := row.get('DDISH_NM')): 
                menu_names.append(v)
                if '(' in v and ')' in v:
                    codes = v[v.find('(')+1:v.find(')')].replace(',', '.').split('.')
                    allergy_codes.extend([c.strip() for c in codes])
        return jsonify({
            "ORPLC_INFO": ', '.join(sorted(set(orplc_info))) or '정보 없음',
            "CAL_INFO": ', '.join(sorted(set(cal_info))) or '정보 없음',
            "NTR_INFO": ', '.join(sorted(set(ntr_info))) or '정보 없음',
            "menu_names": '\n'.join(menu_names) or '정보 없음',
            "allergy": ','.join(sorted(set([c for c in allergy_codes if c])))
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.get_json()
        date = data.get('date', datetime.today().strftime("%Y%m%d"))
        meal_type = data.get('meal_type')
        rating = data.get('rating')
        feedback = data.get('feedback')
        if not meal_type or not rating or not (1 <= int(rating) <= 5):
            return jsonify({"error": "입력 오류"}), 400
        ts = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO meal_feedback (date, meal_type, rating, feedback, timestamp) VALUES (?, ?, ?, ?, ?)" 
            if not DATABASE_URL else
            "INSERT INTO meal_feedback (date, meal_type, rating, feedback, timestamp) VALUES (%s, %s, %s, %s, %s)",
            (date, meal_type, int(rating), feedback, ts)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "피드백 제출 완료"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit_like', methods=['POST'])
def submit_like():
    try:
        data = request.get_json()
        date = data.get('date', datetime.today().strftime("%Y%m%d"))
        meal_type = data.get('meal_type')

        if not meal_type:
            return jsonify({"error": "식사 타입이 필요합니다."}), 400

        # 현재 좋아요 수를 가져옵니다.
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT likes FROM meal_feedback WHERE date = %s AND meal_type = %s LIMIT 1",
            (date, meal_type)
        )
        row = cursor.fetchone()

        # 만약 해당 날짜와 식사 타입에 대한 레코드가 없다면 추가합니다.
        if row:
            likes = row[0]
            cursor.execute(
                "UPDATE meal_feedback SET likes = %s WHERE date = %s AND meal_type = %s",
                (likes + 1, date, meal_type)
            )
        else:
            cursor.execute(
                "INSERT INTO meal_feedback (date, meal_type, likes) VALUES (%s, %s, %s)",
                (date, meal_type, 1)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "좋아요 처리 완료"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_like_count', methods=['GET'])
def get_like_count():
    try:
        date = request.args.get('date', datetime.today().strftime("%Y%m%d"))
        meal_type = request.args.get('meal_type')

        if not meal_type:
            return jsonify({"error": "식사 타입이 필요합니다."}), 400

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT likes FROM meal_feedback WHERE date = %s AND meal_type = %s LIMIT 1",
            (date, meal_type)
        )
        row = cursor.fetchone()

        if row:
            likes = row[0]
            return jsonify({"like_count": likes}), 200
        else:
            return jsonify({"like_count": 0}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return jsonify({"message": "서버 정상 실행 중"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
