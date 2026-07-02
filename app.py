from datetime import date,datetime
from flask import Flask, render_template, request, redirect, session, flash
from excel import save_to_excel
from flask import send_file
from functools import wraps
import sqlite3

app = Flask(__name__)
app.secret_key = "attendance_secret_key"

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login_user():

    username = request.form["username"]
    password = request.form["password"]

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM faculty WHERE username=? AND password=?",
        (username, password)
    )

    user = cursor.fetchone()

    conn.close()

    if user:
        session["user"] = username
        return redirect("/dashboard")

    return render_template(
        "login.html",
        error="Invalid Username or Password"
    )

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/")

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user" not in session:
            return redirect("/")

        return f(*args, **kwargs)

    return decorated_function

@app.route("/students")
@login_required
def students():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")
    data = cursor.fetchall()

    conn.close()
    
    return render_template("students.html", students=data)

@app.route("/attendance")
@login_required
def attendance():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    conn.close()

    return render_template("attendance.html", students=students)


@app.route("/add_student", methods=["POST"])
@login_required
def add_student():

    roll = request.form["roll"]
    name = request.form["name"]
    dept = request.form["department"]
    year = request.form["year"]
    section = request.form["section"]

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO students(roll_no,name,department,year,section) VALUES(?,?,?,?,?)",
        (roll, name, dept, year, section),
    )

    conn.commit()
    conn.close()
    
    flash("Student added successfully!", "success")

    return redirect("/students")

@app.route("/save_attendance", methods=["POST"])
@login_required
def save_attendance():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    today = date.today().strftime("%Y-%m-%d")

    subject = request.form.get("subject", "").strip().title()

    # Get all student IDs from the form
    student_ids = request.form.getlist("student_id")

    for sid in student_ids:

        status = request.form.get(f"status_{sid}")

        # Get student details
        cursor.execute(
            "SELECT roll_no, name FROM students WHERE id = ?",
            (sid,)
        )

        student = cursor.fetchone()

        roll_no = student[0]
        name = student[1]

        # Save attendance to database
        cursor.execute("""
            SELECT * FROM attendance
            WHERE student_id=? AND attendance_date=? AND subject=?
        """, (sid, today, subject) )

        existing = cursor.fetchone()

        if existing is None:

            cursor.execute("""
                INSERT INTO attendance
                (student_id, attendance_date, status, subject)
                VALUES (?, ?, ?, ?)
            """, (sid, today, status, subject))

            save_to_excel(today, subject, roll_no, name, status)

        # Save attendance to Excel

    conn.commit()
    conn.close()
    
    flash("Attendance saved successfully!", "success")
    
    return redirect("/attendance")


@app.route("/view_attendance")
@login_required
def view_attendance():

    selected_date = request.args.get("date")
    subject = request.args.get("subject")

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    query = """
        SELECT attendance.id,
               attendance.attendance_date,
               students.roll_no,
               students.name,
               attendance.subject,
               attendance.status
        FROM attendance
        JOIN students
        ON students.id = attendance.student_id
        WHERE attendance.is_deleted = 0
    """

    params = []

    if selected_date:
        query += " AND attendance.attendance_date = ?"
        params.append(selected_date)

    if subject:
        query += " AND attendance.subject LIKE ?"
        params.append(f"%{subject}%")

    query += " ORDER BY attendance.attendance_date DESC"

    cursor.execute(query, params)

    data = cursor.fetchall()

    conn.close()

    return render_template(
        "view_attendance.html",
        attendance=data,
        selected_date=selected_date,
        subject=subject
    )
    
@app.route("/dashboard")
@login_required
def dashboard():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    today = date.today().strftime("%Y-%m-%d")

    current_time = datetime.now().strftime("%I:%M %p")

    cursor.execute("SELECT COUNT(*) FROM students")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status='Present' AND is_deleted=0",
        (today,)
    )
    present = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status='Absent' AND is_deleted=0",
        (today,)
    )
    absent = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        total=total,
        present=present,
        absent=absent,
        today=today,
        current_time=current_time,
        username=session["user"]
    )

@app.route("/download")
@login_required
def download():

    return send_file(
        "attendance.xlsx",
        as_attachment=True
    )

@app.route("/search")
@login_required
def search():

    keyword = request.args.get("keyword","").strip()

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        WHERE name LIKE ?
        OR roll_no LIKE ?
    """, (f"%{keyword}%", f"%{keyword}%"))

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "students.html",
        students=students
    )

@app.route("/delete_student/<int:id>")
@login_required
def delete_student(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM students WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Student deleted successfully!", "success")

    return redirect("/students")



@app.route("/edit_student/<int:id>")
@login_required
def edit_student(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM students WHERE id=?",
        (id,)
    )

    student = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_student.html",
        student=student
    )

@app.route("/update_student", methods=["POST"])
@login_required
def update_student():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""

    UPDATE students

    SET

    roll_no=?,
    name=?,
    department=?,
    year=?,
    section=?

    WHERE id=?

    """,

    (

        request.form["roll"],
        request.form["name"],
        request.form["department"],
        request.form["year"],
        request.form["section"],
        request.form["id"]

    ))

    conn.commit()
    conn.close()

    flash("Student updated successfully!", "success")


    return redirect("/students")

@app.route("/percentage")
@login_required
def percentage():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        students.roll_no,
        students.name,

        COUNT(attendance.id) AS total_classes,

        SUM(
            CASE
                WHEN attendance.status='Present'
                THEN 1
                ELSE 0
            END
        ) AS present_days

    FROM students

    LEFT JOIN attendance

    ON students.id = attendance.student_id
    AND attendance.is_deleted=0

    GROUP BY students.id
    """)

    data = cursor.fetchall()

    result = []

    for row in data:

        roll = row[0]
        name = row[1]
        total = row[2]
        present = row[3]

        if present is None:
            present = 0

        if total == 0:
            percentage = 0
        else:
            percentage = round((present / total) * 100, 2)

        result.append((roll, name, total, present, percentage))

    conn.close()

    return render_template(
        "percentage.html",
        result=result
    )

@app.route("/edit_attendance/<int:id>")
@login_required
def edit_attendance(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT attendance.id,
               attendance.attendance_date,
               attendance.subject,    
               students.roll_no,
               students.name,
               attendance.status
        FROM attendance
        JOIN students
        ON students.id = attendance.student_id
        WHERE attendance.id=?
    """, (id,))

    attendance = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_attendance.html",
        attendance=attendance
    )

@app.route("/update_attendance", methods=["POST"])
@login_required
def update_attendance():

    attendance_id = request.form["id"]
    status = request.form["status"]

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE attendance
        SET status=?
        WHERE id=?
    """, (status, attendance_id))

    conn.commit()
    conn.close()

    return redirect("/view_attendance")

@app.route("/delete_attendance/<int:id>")
@login_required
def delete_attendance(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE attendance
        SET is_deleted = 1
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/view_attendance")

@app.route("/deleted_attendance")
@login_required
def deleted_attendance():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT attendance.id,
               attendance.attendance_date,
               students.roll_no,
               students.name,
               attendance.status
        FROM attendance
        JOIN students
        ON students.id = attendance.student_id
        WHERE attendance.is_deleted = 1
    """)

    data = cursor.fetchall()

    conn.close()

    return render_template(
        "deleted_attendance.html",
        attendance=data
    )

@app.route("/restore_attendance/<int:id>")
@login_required
def restore_attendance(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE attendance
        SET is_deleted = 0
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/deleted_attendance")


if __name__ == "__main__":
    app.run(debug=True)