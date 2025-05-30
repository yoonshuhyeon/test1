import os
import qrcode
import requests
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 현재 파일 위치 기준으로 상대 경로 지정 (Heroku 호환)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# QR 코드 저장 폴더 생성
QR_FOLDER = os.path.join(BASE_DIR, "qr_codes")
os.makedirs(QR_FOLDER, exist_ok=True)

# 데이터베이스 파일 경로
DB_PATH = os.path.join(BASE_DIR, "feedback.db")

# NEIS API 관련 정보 (본인 정보로 수정)
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
MEAL_API_KEY = "368ccd7447b04140b197c937a072fb76"
ATPT_OFCDC_SC_CODE = "T10"   # 교육청 코드 (예: 서울특별시)
SD_SCHUL_CODE = "9290055"    # 학교 코드 (본인 학교 코드로 변경)

def init_feedback_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            rating INTEGER NOT NULL,
            feedback TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_feedback_db()

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    grade = str(data.get('grade', '')).strip()
    class_num = str(data.get('class_num', '')).strip()
    student_num = str(data.get('student_num', '')).strip()
    name = str(data.get('name', '')).strip()

    if not (grade.isdigit() and class_num.isdigit() and student_num.isdigit() and name):
        return jsonify({"error": "학년, 반, 번호는 숫자, 이름은 반드시 입력해주세요."}), 400

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
    date_str = request.args.get('date')
    if not date_str:
        date_str = datetime.today().strftime("%Y%m%d")

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

        meal_service = data.get('mealServiceDietInfo')
        if meal_service and len(meal_service) > 1:
            meal_data = meal_service[1].get('row', [])
            for meal in meal_data:
                meal_type = meal.get('MMEAL_SC_NM', '')
                dish_name = meal.get('DDISH_NM', '')
                if meal_type == '중식':
                    meal_info['lunch'] = dish_name
                elif meal_type == '석식':
                    meal_info['dinner'] = dish_name
        else:
            meal_info['error'] = "급식 정보가 없습니다."

        return jsonify(meal_info)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/nutrition', methods=['GET'])
def get_nutrition():
    date_str = request.args.get('date')
    if not date_str:
        date_str = datetime.today().strftime("%Y%m%d")

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

        meal_service = data.get('mealServiceDietInfo')
        if not meal_service or len(meal_service) < 2:
            return jsonify({"error": "급식 정보가 없습니다."}), 404

        meal_rows = meal_service[1].get('row', [])
        if not meal_rows:
            return jsonify({"error": "급식 정보가 없습니다."}), 404

        orplc_info = []
        cal_info = []
        ntr_info = []
        menu_names = []
        allergy_codes_list = []

        for row in meal_rows:
            orplc = row.get('ORPLC_INFO', '')
            if orplc:
                orplc_info.append(orplc)

            cal = row.get('CAL_INFO', '')
            if cal:
                cal_info.append(cal)

            ntr = row.get('NTR_INFO', '')
            if ntr:
                ntr_info.append(ntr)

            dish_name = row.get('DDISH_NM', '')
            if dish_name:
                menu_names.append(dish_name)

                start = dish_name.find('(')
                end = dish_name.find(')')
                if start != -1 and end != -1 and start < end:
                    codes_str = dish_name[start+1:end]
                    codes = [code.strip() for code in codes_str.replace(',', '.').split('.')]
                    allergy_codes_list.extend(codes)

        orplc_info_str = ', '.join(sorted(set(orplc_info))) if orplc_info else '정보 없음'
        cal_info_str = ', '.join(sorted(set(cal_info))) if cal_info else '정보 없음'
        ntr_info_str = ', '.join(sorted(set(ntr_info))) if ntr_info else '정보 없음'
        menu_names_str = '\n'.join(menu_names) if menu_names else '정보 없음'

        allergy_codes_list = [code for code in allergy_codes_list if code]
        all_codes_unique = ','.join(sorted(set(allergy_codes_list))) if allergy_codes_list else ''

        return jsonify({
            "ORPLC_INFO": orplc_info_str,
            "CAL_INFO": cal_info_str,
            "NTR_INFO": ntr_info_str,
            "menu_names": menu_names_str,
            "allergy": all_codes_unique
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

        if not meal_type or not rating:
            return jsonify({"error": "급식 종류와 평점은 필수입니다."}), 400

        if not (1 <= int(rating) <= 5):
            return jsonify({"error": "평점은 1~5 사이의 숫자여야 합니다."}), 400

        kst_now = datetime.utcnow() + timedelta(hours=9)
        kst_timestamp_str = kst_now.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO meal_feedback (date, meal_type, rating, feedback, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (date, meal_type, int(rating), feedback, kst_timestamp_str))
        conn.commit()
        conn.close()

        return jsonify({"message": "피드백이 성공적으로 제출되었습니다."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_feedback', methods=['GET'])
def get_feedback():
    try:
        date = request.args.get('date', datetime.today().strftime("%Y%m%d"))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT meal_type, AVG(rating) as avg_rating, COUNT(*) as count
            FROM meal_feedback 
            WHERE date = ? 
            GROUP BY meal_type
        """, (date,))

        results = cursor.fetchall()

        feedback_data = {}
        for row in results:
            meal_type, avg_rating, count = row
            feedback_data[meal_type] = {
                'average_rating': round(avg_rating, 1),
                'total_reviews': count
            }

        conn.close()
        return jsonify(feedback_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_feedback_details', methods=['GET'])
def get_feedback_details():
    try:
        date = request.args.get('date', datetime.today().strftime("%Y%m%d"))
        meal_type = request.args.get('meal_type')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if meal_type:
            cursor.execute("""
                SELECT rating, feedback, timestamp 
                FROM meal_feedback 
                WHERE date = ? AND meal_type = ?
                ORDER BY timestamp DESC
            """, (date, meal_type))
        else:
            cursor.execute("""
                SELECT meal_type, rating, feedback, timestamp 
                FROM meal_feedback 
                WHERE date = ?
                ORDER BY timestamp DESC
            """, (date,))

        results = cursor.fetchall()

        feedback_list = []
        for row in results:
            if meal_type:
                rating, feedback, timestamp = row
                feedback_list.append({
                    'rating': rating,
                    'feedback': feedback,
                    'timestamp': timestamp
                })
            else:
                meal_type_val, rating, feedback, timestamp = row
                feedback_list.append({
                    'meal_type': meal_type_val,
                    'rating': rating,
                    'feedback': feedback,
                    'timestamp': timestamp
                })

        conn.close()
        return jsonify({'feedback_list': feedback_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return jsonify({"message": "서버 정상 실행 중"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
