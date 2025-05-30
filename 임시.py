import os
import sqlite3
import tkinter as tk
from tkinter import messagebox
import tkinter.ttk as ttk
import qrcode


db_path = "/Users/suhyeon/Documents/code/python/프로젝트2/students.db"

# QR코드 저장 폴더
qr_folder = "qr_codes"
os.makedirs(qr_folder, exist_ok=True)

def init_db():
    conn = sqlite3.connect(db_path)
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
    conn.commit()
    conn.close()

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)

def save_data(grade, class_num, student_num, name):
    if not (grade.isdigit() and class_num.isdigit() and student_num.isdigit() and name.strip()):
        messagebox.showerror("입력 오류", "모든 항목을 올바르게 입력해주세요.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students WHERE grade=? AND class_num=? AND student_num=?
    """, (int(grade), int(class_num), int(student_num)))
    if cursor.fetchone():
        messagebox.showerror("중복 오류", "이미 존재하는 학생입니다.")
        conn.close()
        return

    cursor.execute("""
        INSERT INTO students (grade, class_num, student_num, name)
        VALUES (?, ?, ?, ?)
    """, (int(grade), int(class_num), int(student_num), name.strip()))
    conn.commit()
    conn.close()

    # QR코드 생성
    qr_data = f"{grade}_{class_num}_{student_num}"
    qr_filename = os.path.join(qr_folder, f"{qr_data}.png")
    generate_qr_code(qr_data, qr_filename)

    messagebox.showinfo("저장 완료", f"{name} 학생 정보가 저장되고 QR코드가 생성되었습니다.\n파일 위치: {qr_filename}")

def password():
    pw_window = tk.Toplevel(root)
    pw_window.title("비밀번호 입력")
    pw_window.geometry("300x150")

    password_label = tk.Label(pw_window, text="비밀번호 입력:")
    password_label.pack(pady=10)

    password_entry = tk.Entry(pw_window, show="*")
    password_entry.pack(pady=10)
    password_entry.focus_set()

    password_button = tk.Button(pw_window, text="확인", command=lambda: check_password(pw_window, password_entry))
    password_button.pack(pady=10)

def check_password(pw_window, password_entry):
    password = password_entry.get()
    if password == "123800" or password == "0000":
        pw_window.destroy()
        show_all_students()
    else:
        messagebox.showerror("비밀번호 오류", "잘못된 비밀번호 입니다.")
        password_entry.delete(0, tk.END)

all_window = None  # 전역변수
tree = None

def show_all_students():
    global all_window, tree
    if all_window is not None and all_window.winfo_exists():
        all_window.lift()
        refresh_treeview()
        return

    all_window = tk.Toplevel(root)
    all_window.title("전체 학생 정보")
    all_window.geometry("600x400")

    columns = ("grade", "class_num", "student_num", "name")
    tree = ttk.Treeview(all_window, columns=columns, show='headings')

    tree.heading("grade", text="학년")
    tree.heading("class_num", text="반")
    tree.heading("student_num", text="번호")
    tree.heading("name", text="이름")

    tree.column("grade", width=50, anchor='center')
    tree.column("class_num", width=50, anchor='center')
    tree.column("student_num", width=50, anchor='center')
    tree.column("name", width=200, anchor='w')

    tree.pack(fill='both', expand=True, padx=10, pady=10)

    context_menu = tk.Menu(all_window, tearoff=0)

    def delete_selected():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("경고", "삭제할 학생을 선택하세요.")
            return

        confirm = messagebox.askyesno("삭제 확인", "선택한 학생 정보를 정말 삭제하시겠습니까?")
        if not confirm:
            return

        item = selected_item[0]
        values = tree.item(item, "values")
        grade, class_num, student_num, name = values

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM students WHERE grade=? AND class_num=? AND student_num=?
        """, (grade, class_num, student_num))
        conn.commit()
        conn.close()

        tree.delete(item)
        messagebox.showinfo("삭제 완료", f"{name} 학생 정보가 삭제되었습니다.")

    context_menu.add_command(label="삭제하기", command=delete_selected)

    def on_right_click(event):
        selected_item = tree.identify_row(event.y)
        if selected_item:
            tree.selection_set(selected_item)
            context_menu.post(event.x_root, event.y_root)

    tree.bind("<Button-3>", on_right_click)
    tree.bind("<Control-Button-1>", on_right_click)

    refresh_treeview()

def refresh_treeview():
    global tree
    if tree is None:
        return

    for item in tree.get_children():
        tree.delete(item)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT grade, class_num, student_num, name FROM students ORDER BY grade, class_num, student_num")
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        tree.insert("", "end", values=row)

root = tk.Tk()
root.title("학생 정보 입력 및 관리")
root.attributes("-fullscreen", True)

tk.Label(root, text="학년:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
grade_var = tk.StringVar(value="학년 선택")
grade_menu = tk.OptionMenu(root, grade_var, "1", "2", "3")
grade_menu.grid(row=0, column=1, padx=10, pady=10)


tk.Label(root, text="반:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
class_var = tk.StringVar(value="반 선택")
class_menu = tk.OptionMenu(root, class_var, *[str(i) for i in range(1, 9)])
class_menu.grid(row=1, column=1, padx=10, pady=10)

tk.Label(root, text="번호:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
num_var = tk.StringVar(value="번호 선택")
num_menu = tk.OptionMenu(root, num_var, *[str(i) for i in range(1, 31)])
num_menu.grid(row=2, column=1, padx=10, pady=10)

tk.Label(root, text="이름:").grid(row=3, column=0, padx=10, pady=10, sticky="e")
name_entry = tk.Entry(root)
name_entry.grid(row=3, column=1, padx=10, pady=10)

save_button = tk.Button(root, text="저장", command=lambda: save_data(grade_var.get(), class_var.get(), num_var.get(), name_entry.get()))
save_button.grid(row=6, column=1, padx=20, pady=10)

all_button = tk.Button(root, text="전체 학생 조회", command=password)
all_button.grid(row=8, column=1, padx=20, pady=10)
tk.Label(root, text="전체 학생 조회").grid(row=8, column=0, padx=10, pady=10, sticky="e")

init_db()
root.mainloop()
