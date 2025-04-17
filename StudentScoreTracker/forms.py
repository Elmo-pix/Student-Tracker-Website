from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, DateField, RadioField
from wtforms.validators import DataRequired, Email, Length, Optional

class LoginForm(FlaskForm):
    user_type = SelectField('User Type', choices=[('admin', 'Admin'), ('student', 'Student')], validators=[DataRequired()])
    username = StringField('Username/Student Number', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class StudentForm(FlaskForm):
    student_number = StringField('Student Number', validators=[DataRequired(), Length(min=3, max=20)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[Email(), Length(max=100), Optional()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Add Student')

class QuizForm(FlaskForm):
    title = StringField('Quiz Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    time_limit = IntegerField('Time Limit (minutes)', validators=[Optional()])
    submit = SubmitField('Create Quiz')

class QuestionForm(FlaskForm):
    question_text = TextAreaField('Question', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('short_answer', 'Short Answer')
    ], validators=[DataRequired()])
    option_a = StringField('Option A', validators=[Optional()])
    option_b = StringField('Option B', validators=[Optional()])
    option_c = StringField('Option C', validators=[Optional()])
    option_d = StringField('Option D', validators=[Optional()])
    correct_answer = StringField('Correct Answer (For multiple choice, use A, B, C, or D)', validators=[DataRequired()])
    points = IntegerField('Points', default=1, validators=[DataRequired()])
    submit = SubmitField('Add Question')

class AttendanceForm(FlaskForm):
    student_id = SelectField('Student', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late')
    ], validators=[DataRequired()])
    submit = SubmitField('Record Attendance')
