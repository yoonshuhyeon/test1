import os
import cv2
import sqlite3
from pyzbar.pyzbar import decode
import pygame
import time
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "students.db")

pygame.mixer.init()
sound_ok = pygame.mixer.Sound(os.path.join(BASE_DIR, "ok_sound.wav"))
sound_fail = pygame.mixer.Sound(os.path.join(BASE_DIR, "fail_sound.wav"))

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grade INTEGER,
                    class_num INTEGER,
                    student_num INTEGER,
                    name TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meal_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grade INTEGER,
                    class_num INTEGER,
                    student_num INTEGER,
                    name TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()
    except Exception as e:
        print("DB 초기화 오류:", e)

def check_student_in_db(qr_data):
    try:
        grade, class_num, student_num = qr_data.split('_')
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM students WHERE grade=? AND class_num=? AND student_num=?", 
                (int(grade), int(class_num), int(student_num))
            )
            student = cursor.fetchone()
        if student:
            return (int(grade), int(class_num), int(student_num), student[0])
        else:
            return None
    except Exception as e:
        print("학생 조회 오류:", e)
        return None

def log_meal_to_db(grade, class_num, student_num, name):
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO meal_logs (grade, class_num, student_num, name, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (grade, class_num, student_num, name, timestamp))
            conn.commit()
    except Exception as e:
        print("로그 저장 오류:", e)

def qr_scanner():
    cap = cv2.VideoCapture(0)
    cooldown = 2  # seconds
    last_result_time = time.time()
    show_color = None
    last_qr_data = ""

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        barcodes = decode(frame)

        if barcodes:
            try:
                qr_data = barcodes[0].data.decode('utf-8')
            except Exception as e:
                print("QR 데이터 디코딩 오류:", e)
                qr_data = None

            if qr_data and (qr_data != last_qr_data or current_time - last_result_time > cooldown):
                student_info = check_student_in_db(qr_data)
                if student_info:
                    grade, class_num, student_num, name = student_info
                    show_color = "green"
                    sound_ok.play()
                    log_meal_to_db(grade, class_num, student_num, name)
                else:
                    show_color = "red"
                    sound_fail.play()
                last_result_time = current_time
                last_qr_data = qr_data
        else:
            if current_time - last_result_time > cooldown:
                show_color = None
                last_qr_data = ""

        if show_color == "green":
            overlay = np.full(frame.shape, (0, 255, 0), dtype=np.uint8)
            alpha = 0.6
            frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        elif show_color == "red":
            overlay = np.full(frame.shape, (0, 0, 255), dtype=np.uint8)
            alpha = 0.6
            frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        cv2.imshow("QR 코드 스캔", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    init_db()
    qr_scanner()
