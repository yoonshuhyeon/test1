import cv2
from pyzbar.pyzbar import decode
import psycopg2
import os
from urllib.parse import urlparse, parse_qs
from playsound import playsound

# 환경변수에서 DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    result = urlparse(DATABASE_URL)
    return psycopg2.connect(
        dbname=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )

def check_student(grade, class_num, student_num):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM students WHERE grade=%s AND class_num=%s AND student_num=%s",
        (grade, class_num, student_num)
    )
    result = cur.fetchone()
    conn.close()
    return result is not None

def extract_info_from_qr(qrdata):
    # "1_2_15" 같은 형식
    if "_" in qrdata:
        parts = qrdata.split("_")
        if len(parts) == 3:
            return parts
    # URL query string 형식
    if "grade=" in qrdata and "class=" in qrdata and "num=" in qrdata:
        query = qrdata.split("?", 1)[-1]
        params = parse_qs(query)
        grade = params.get("grade", [""])[0]
        class_num = params.get("class", [""])[0]
        student_num = params.get("num", [""])[0]
        return (grade, class_num, student_num)
    return (None, None, None)

def main():
    cap = cv2.VideoCapture(0)
    print("QR코드를 카메라에 비춰주세요. ESC로 종료")
    success_sound = "/Users/suhyeon/Documents/code/ok_sound.wav"  # 본인 파일명으로 수정
    fail_sound = "/Users/suhyeon/Documents/code/fail_sound.wav"        # 본인 파일명으로 수정

    last_result = None  # 중복 인식 방지

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        decoded_objs = decode(frame)
        found = False
        for obj in decoded_objs:
            qrdata = obj.data.decode("utf-8")
            grade, class_num, student_num = extract_info_from_qr(qrdata)
            if not all([grade, class_num, student_num]):
                continue
            if last_result == qrdata:
                continue  # 같은 QR 반복 인식 방지
            last_result = qrdata
            if check_student(grade, class_num, student_num):
                color = (0, 255, 0)  # 초록
                msg = "성공했습니다"
                playsound(success_sound, block=False)
            else:
                color = (0, 0, 255)  # 빨강
                msg = "실패했습니다"
                playsound(fail_sound, block=False)
            found = True
            # QR 위치에 사각형 및 텍스트 표시
            pts = obj.polygon
            if len(pts) == 4:
                pts = [(pt.x, pt.y) for pt in pts]
                cv2.polylines(frame, [np.array(pts, np.int32)], True, color, 5)
            cv2.putText(frame, msg, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 5)
        if not found:
            last_result = None  # 새 인식을 위해 초기화
        cv2.imshow("QR 체크", frame)
        if cv2.waitKey(1) == 27:  # ESC키로 종료
            break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import numpy as np  # polylines용
    main()
