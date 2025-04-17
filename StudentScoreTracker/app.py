import os
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, session, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import pandas as pd
import io
import csv

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Setup the database
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///student_management.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create all tables
with app.app_context():
    import models  # noqa: F401
    db.create_all()

# Import routes after database initialization to avoid circular imports
from forms import LoginForm, StudentForm, QuizForm, QuestionForm, AttendanceForm
from models import User, Student, Attendance, Quiz, Question, QuizResult, QuizAnswer
from utils import generate_csv, generate_pdf

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create a default admin user if none exists
def create_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            role='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        app.logger.info('Admin user created')

# Create default admin in app context
with app.app_context():
    create_admin()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        # Admin login
        if form.user_type.data == 'admin':
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.role == 'admin' and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                app.logger.info(f'Admin {user.username} logged in')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'danger')
        
        # Student login
        else:
            student = Student.query.filter_by(student_number=form.username.data).first()
            if student and check_password_hash(student.password_hash, form.password.data):
                # Create or get user record for the student
                user = User.query.filter_by(username=student.student_number).first()
                if not user:
                    user = User(
                        username=student.student_number,
                        role='student',
                        password_hash=student.password_hash
                    )
                    db.session.add(user)
                    db.session.commit()
                login_user(user)
                session['student_id'] = student.id
                app.logger.info(f'Student {student.student_number} logged in')
                return redirect(url_for('student_dashboard'))
            else:
                flash('Invalid student number or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('student_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Admin routes
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get some stats for the dashboard
    student_count = Student.query.count()
    attendance_today = Attendance.query.filter_by(date=datetime.today().date()).count()
    recent_quizzes = Quiz.query.order_by(Quiz.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          student_count=student_count, 
                          attendance_today=attendance_today,
                          recent_quizzes=recent_quizzes)

@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    form = StudentForm()
    if form.validate_on_submit():
        # Check if student number is already used
        existing_student = Student.query.filter_by(student_number=form.student_number.data).first()
        if existing_student:
            flash('Student number already exists', 'danger')
        else:
            student = Student(
                student_number=form.student_number.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data)
            )
            db.session.add(student)
            db.session.commit()
            flash('Student added successfully', 'success')
            return redirect(url_for('students'))
    
    students_list = Student.query.all()
    return render_template('students.html', form=form, students=students_list)

@app.route('/students/delete/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    flash('Student deleted successfully', 'success')
    return redirect(url_for('students'))

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    form = AttendanceForm()
    form.student_id.choices = [(s.id, f"{s.student_number} - {s.first_name} {s.last_name}") 
                               for s in Student.query.all()]
    
    if form.validate_on_submit():
        # Check if attendance already recorded for this student on this date
        existing = Attendance.query.filter_by(
            student_id=form.student_id.data,
            date=form.date.data
        ).first()
        
        if existing:
            flash('Attendance already recorded for this student on this date', 'warning')
        else:
            attendance = Attendance(
                student_id=form.student_id.data,
                date=form.date.data,
                status=form.status.data
            )
            db.session.add(attendance)
            db.session.commit()
            flash('Attendance recorded successfully', 'success')
            return redirect(url_for('attendance'))
    
    # Get attendance records
    attendance_records = db.session.query(
        Attendance, Student
    ).join(Student).order_by(Attendance.date.desc()).all()
    
    return render_template('attendance.html', form=form, attendance_records=attendance_records)

@app.route('/attendance/export', methods=['GET'])
@login_required
def export_attendance():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get attendance records with student information
    records = db.session.query(
        Attendance.date,
        Attendance.status,
        Student.student_number,
        Student.first_name,
        Student.last_name
    ).join(Student).order_by(Attendance.date.desc()).all()
    
    # Convert to DataFrame
    df = pd.DataFrame(records, columns=['Date', 'Status', 'Student Number', 'First Name', 'Last Name'])
    
    # Export as CSV
    csv_data = generate_csv(df)
    
    return send_file(
        csv_data,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'attendance-{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

@app.route('/quizzes', methods=['GET', 'POST'])
@login_required
def quizzes():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    form = QuizForm()
    if form.validate_on_submit():
        quiz = Quiz(
            title=form.title.data,
            description=form.description.data,
            time_limit=form.time_limit.data
        )
        db.session.add(quiz)
        db.session.commit()
        flash('Quiz created successfully', 'success')
        return redirect(url_for('edit_quiz', id=quiz.id))
    
    quizzes_list = Quiz.query.order_by(Quiz.created_at.desc()).all()
    return render_template('quizzes.html', form=form, quizzes=quizzes_list)

@app.route('/quizzes/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_quiz(id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    quiz = Quiz.query.get_or_404(id)
    form = QuestionForm()
    
    if form.validate_on_submit():
        question = Question(
            quiz_id=quiz.id,
            question_text=form.question_text.data,
            question_type=form.question_type.data,
            option_a=form.option_a.data if form.question_type.data == 'multiple_choice' else None,
            option_b=form.option_b.data if form.question_type.data == 'multiple_choice' else None,
            option_c=form.option_c.data if form.question_type.data == 'multiple_choice' else None,
            option_d=form.option_d.data if form.question_type.data == 'multiple_choice' else None,
            correct_answer=form.correct_answer.data,
            points=form.points.data
        )
        db.session.add(question)
        db.session.commit()
        flash('Question added successfully', 'success')
        return redirect(url_for('edit_quiz', id=quiz.id))
    
    questions = Question.query.filter_by(quiz_id=quiz.id).all()
    return render_template('edit_quiz.html', quiz=quiz, form=form, questions=questions)

@app.route('/quizzes/delete/<int:id>', methods=['POST'])
@login_required
def delete_quiz(id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    quiz = Quiz.query.get_or_404(id)
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted successfully', 'success')
    return redirect(url_for('quizzes'))

@app.route('/questions/delete/<int:id>', methods=['POST'])
@login_required
def delete_question(id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    question = Question.query.get_or_404(id)
    quiz_id = question.quiz_id
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully', 'success')
    return redirect(url_for('edit_quiz', id=quiz_id))

@app.route('/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    students = Student.query.all()
    quizzes = Quiz.query.all()
    
    return render_template('reports.html', students=students, quizzes=quizzes)

@app.route('/reports/student/<int:id>')
@login_required
def student_report(id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student = Student.query.get_or_404(id)
    
    # Get attendance records
    attendance = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).all()
    
    # Get quiz results
    results = db.session.query(
        QuizResult, Quiz
    ).join(Quiz).filter(QuizResult.student_id == student.id).all()
    
    # Prepare data for CSV export
    attendance_data = pd.DataFrame(
        [(a.date, a.status) for a in attendance],
        columns=['Date', 'Status']
    )
    
    quiz_data = pd.DataFrame(
        [(r[1].title, r[0].score, r[0].completed_at) for r in results],
        columns=['Quiz', 'Score', 'Completed At']
    )
    
    combined_data = {
        'Student': f"{student.student_number} - {student.first_name} {student.last_name}",
        'Attendance': attendance_data.to_dict(),
        'Quiz Results': quiz_data.to_dict()
    }
    
    # Generate CSV
    csv_data = generate_csv(combined_data)
    
    # Return as CSV
    return send_file(
        csv_data,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'report-{student.student_number}-{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

@app.route('/reports/quiz/<int:id>')
@login_required
def quiz_report(id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    quiz = Quiz.query.get_or_404(id)
    
    # Get all results for this quiz
    results = db.session.query(
        QuizResult, Student
    ).join(Student).filter(QuizResult.quiz_id == quiz.id).order_by(QuizResult.score.desc()).all()
    
    # Prepare data for CSV export
    data = pd.DataFrame(
        [(r[1].student_number, f"{r[1].first_name} {r[1].last_name}", r[0].score, r[0].completed_at) 
         for r in results],
        columns=['Student Number', 'Name', 'Score', 'Completed At']
    )
    
    # Generate CSV
    csv_data = generate_csv(data)
    
    # Return as CSV
    return send_file(
        csv_data,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'quiz-results-{quiz.id}-{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

# Student routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student' or 'student_id' not in session:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student_id = session['student_id']
    student = Student.query.get(student_id)
    
    # Get attendance records
    attendance = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.date.desc()).limit(10).all()
    
    # Get available quizzes
    completed_quiz_ids = [r.quiz_id for r in QuizResult.query.filter_by(student_id=student_id).all()]
    available_quizzes = Quiz.query.filter(~Quiz.id.in_(completed_quiz_ids)).all() if completed_quiz_ids else Quiz.query.all()
    
    # Get completed quizzes
    completed_quizzes = db.session.query(
        Quiz, QuizResult
    ).join(QuizResult).filter(QuizResult.student_id == student_id).all()
    
    return render_template('student_dashboard.html', 
                          student=student, 
                          attendance=attendance,
                          available_quizzes=available_quizzes,
                          completed_quizzes=completed_quizzes)

@app.route('/student/take_quiz/<int:id>', methods=['GET', 'POST'])
@login_required
def take_quiz(id):
    if current_user.role != 'student' or 'student_id' not in session:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student_id = session['student_id']
    
    # Check if quiz already completed
    existing_result = QuizResult.query.filter_by(student_id=student_id, quiz_id=id).first()
    if existing_result:
        flash('You have already completed this quiz', 'warning')
        return redirect(url_for('student_dashboard'))
    
    quiz = Quiz.query.get_or_404(id)
    questions = Question.query.filter_by(quiz_id=id).all()
    
    if not questions:
        flash('This quiz has no questions yet', 'warning')
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        # Calculate score
        score = 0
        total_points = sum(q.points for q in questions)
        
        # Process answers
        for question in questions:
            answer_key = f'question_{question.id}'
            if answer_key in request.form:
                user_answer = request.form[answer_key]
                
                # Check if answer is correct for multiple choice
                if question.question_type == 'multiple_choice':
                    is_correct = user_answer == question.correct_answer
                    if is_correct:
                        score += question.points
                
                # Store the answer
                answer = QuizAnswer(
                    quiz_id=id,
                    question_id=question.id,
                    student_id=student_id,
                    answer_text=user_answer
                )
                db.session.add(answer)
        
        # Create quiz result
        result = QuizResult(
            quiz_id=id,
            student_id=student_id,
            score=score,
            total_points=total_points,
            completed_at=datetime.now()
        )
        db.session.add(result)
        db.session.commit()
        
        flash(f'Quiz completed! Your score: {score}/{total_points}', 'success')
        return redirect(url_for('student_dashboard'))
    
    return render_template('take_quiz.html', quiz=quiz, questions=questions)

# Start the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
