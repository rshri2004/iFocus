from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from openai import OpenAI

from app import app, db, login_manager
from models import User, Assignment, Enrollment, Note, FocusData
from werkzeug.security import generate_password_hash, check_password_hash
from youtube_transcript_api import YouTubeTranscriptApi
import pdfplumber
import os
import openai
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from langchain_ollama import ChatOllama


# home, login, logout, register pages
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        if current_user and current_user.is_authenticated:
            if current_user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif current_user.role == 'Student':
                return redirect(url_for('student_dashboard'))
            elif current_user.role == 'Teacher':
                return redirect(url_for('teacher_dashboard'))

    return render_template("login.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Fetch the user from the database
        user = User.query.filter_by(username=username).first()

        # Check if user exists and the password is correct
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'Student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'Teacher':
                return redirect(url_for('teacher_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    elif request.method == 'GET':
        if current_user and current_user.is_authenticated:
            if current_user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif current_user.role == 'Student':
                return redirect(url_for('student_dashboard'))
            elif current_user.role == 'Teacher':
                return redirect(url_for('teacher_dashboard'))
        else:
            return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    # Flash a success message for user feedback
    flash('You have been logged out successfully.', 'success')
    # Redirect the user to the login page
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        # Check if the username is already taken
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        # Create a new user
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            role=role
        )

        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please sign in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

## Student routes and methods
@app.route('/student_dashboard', methods=['GET', 'POST'])
@login_required
def student_dashboard():
    if current_user.role != 'Student':
        flash('You do not have permission to access the student dashboard.', 'danger')
        return redirect(url_for('login'))

    # Fetch all assignments the current student is enrolled in
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()

    # Fetch assignments and check for insights
    assignments = []
    for enrollment in enrollments:
        assignments.append({
            "id": enrollment.assignment.id,
            "title": enrollment.assignment.title,
            "insights_available": bool(enrollment.insights)  # Check if insights are available
        })

    return render_template('student_dashboard.html', assignments=assignments)


@app.route('/student/insights/<int:assignment_id>')
@login_required
def student_insights(assignment_id):
    if current_user.role != 'Student':
        flash('You do not have permission to access the student dashboard.', 'danger')
        return redirect(url_for('login'))

    # Fetch the enrollment record for the current user and the assignment
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, assignment_id=assignment_id).first()

    if not enrollment or not enrollment.insights:
        flash("Insights not available for this assignment.", "warning")
        return redirect(url_for('student_dashboard'))

    # Path to the heatmap file
    heatmap_path = f'static/heatmaps/heatmap_user_{current_user.id}_assignment_{assignment_id}.png'

    # Check if heatmap exists
    if not os.path.exists(heatmap_path):
        flash("Heatmap not available for this assignment.", "warning")
        return redirect(url_for('student_dashboard'))

    return render_template('student_insights.html', heatmap_file=f'heatmaps/heatmap_user_{current_user.id}_assignment_{assignment_id}.png', enrollment=enrollment)

@app.route('/student-assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def student_assignment_details(assignment_id):
    if current_user.role != 'Student':
        flash('You do not have permission to access student dashboard.', 'danger')
        return redirect(url_for('login'))

    assignment = Assignment.query.get_or_404(assignment_id)
    note = Note.query.filter_by(assignment_id=assignment.id, user_id=current_user.id).first()

    pdf_filename = assignment.pdf_path.split('/')[-1] if assignment.pdf_path else None

    if request.method == 'POST':
        # Handle saving notes for the assignment
        note_content = request.form['note_content']

        if note:
            # Update existing note
            note.text = note_content
        else:
            # Create a new note
            new_note = Note(text=note_content, assignment_id=assignment.id, user_id=current_user.id)
            db.session.add(new_note)
        db.session.commit()

        #flash('Note has been saved successfully!')
        #return redirect(url_for('student_assignment_details', assignment_id=assignment.id))
        return jsonify(success=True, message="Note has been saved successfully!", note_content=note_content)

    return render_template('student_assignment_details.html', assignment=assignment, pdf_filename=pdf_filename, note=note)


## Teacher routes and methods

def summarize_text(text):
    """
    Summarize text using the selected LLM model based on the LLM_MODEL environment variable.
    Defaults to the OpenAI method if the environment variable is not set.
    """
    llm_model = os.getenv("LLM_MODEL", "openai").lower()

    if llm_model == "llama":
        return summarize_text_llama(text)
    else:
        return summarize_text_openai(text)
def summarize_text_llama(text):
    llm = ChatOllama(
        model="llama3.2",
        temperature=0
    )
    messages = [
        (
            "system",
            "You are an assistant that summarizes long transcripts into concise summaries.Please use the same front size as text for header sections. "
        ),
        ("human", f"Summarize the following text in rich text format in {200} words:\n\n{text}"),
    ]
    ai_msg = llm.invoke(messages)
    return ai_msg.content

def summarize_text_openai(text):
    """
    Summarize text using the OpenAI Chat API.
    """
    # Set your OpenAI API key
    openai.api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=openai.api_key)
    model = "gpt-4"
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that summarizes long transcripts into concise summaries."
        },
        {
            "role": "user",
            "content": f"Summarize the following text in rich text format in {200} words:\n\n{text}"
        }
    ]

    try:
        response = client.chat.completions.create(
            messages=messages,
            model=model,
        )
        notes_content = "This is an AI generated notes. Please feel free to update...\n\n" + response.choices[0].message.content
        return notes_content
    except Exception as e:
        print(f"Error summarizing text: {str(e)}")
        return None

def fetch_youtube_transcription(youtube_url):
    """
    Fetch captions from YouTube and summarize them using OpenAI.
    """
    video_id = youtube_url.split("v=")[1].split("&")[0]
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    full_text = " ".join([item['text'] for item in transcript])
    return summarize_text(full_text)

def process_pdf(file_path):
    """
    Extract text from a PDF file and summarize it using OpenAI.
    """
    with pdfplumber.open(file_path) as pdf:
        full_text = " ".join(page.extract_text() for page in pdf.pages if page.extract_text())
    return summarize_text(full_text)

@app.route('/teacher_dashboard', methods=['GET', 'POST'])
@login_required
def teacher_dashboard():
    if current_user.role != 'Teacher':
        flash('You do not have permission to access teacher dashboard.', 'danger')
        return redirect(url_for('login'))

    tab = request.args.get('tab', 'list-assignments') # default tab
    assignments = Assignment.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher_dashboard.html', assignments=assignments, active_tab=tab)

@app.route('/assignment/<int:assignment_id>')
@login_required
def view_assignment(assignment_id):
    if current_user.role != 'Teacher':
        flash('You do not have permission to access teacher dashboard.', 'danger')
        return redirect(url_for('login'))

    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.teacher_id != current_user.id:
        flash('You do not have permission to view this assignment.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    students = [enrollment.user for enrollment in assignment.enrollments]
    return render_template('assignment_detail.html', assignment=assignment, students=students)

@app.route('/submit_assignment', methods=['POST'])
@login_required
def submit_assignment():
    if current_user.role != "Teacher":
        flash('You do not have permission to view this assignment.', 'danger')
        return redirect(url_for('login'))

    title = request.form['title']
    assignment_type = request.form['type']
    pdf_file = request.files.get('pdf_file')
    youtube_url = request.form.get('youtube_url')
    summary = None


    # Validate assignment type
    if assignment_type == 'pdf' and pdf_file:
        file_path = os.path.join(os.getcwd(),'static/uploads/pdfs', pdf_file.filename)
        pdf_file.save(file_path)
        summary = process_pdf(file_path)
        new_assignment = Assignment(title=title, pdf_path=file_path, teacher_id=current_user.id)
    elif assignment_type == 'youtube' and youtube_url:
        summary = fetch_youtube_transcription(youtube_url)
        new_assignment = Assignment(title=title, youtube_url=youtube_url, teacher_id=current_user.id)
    else:
        flash("Invalid assignment data.", "error")
        return redirect(url_for('submit_assignment_form'))

    db.session.add(new_assignment)
    db.session.commit()

    # Store the summary in the database (add a summary column if needed)
    new_assignment.summary = summary  # Ensure this column exists in the Assignment model
    db.session.commit()

    flash("Assignment successfully submitted!", "success")
    return redirect(url_for('teacher_dashboard', tab='list-assignments'))

@app.route('/add_students_to_assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def add_students_to_assignment(assignment_id):
    if current_user.role != 'Teacher':
        flash("You are not authorized to perform this action.", "danger")
        return redirect(url_for('login'))

    # Fetch the assignment
    assignment = Assignment.query.get_or_404(assignment_id)

    # Fetch all students who are not already enrolled in the assignment
    students = User.query.filter_by(role="Student").all()
    existing_enrollments = [enrollment.user for enrollment in assignment.enrollments]

    # Exclude already enrolled students
    available_students = [student for student in students if student not in existing_enrollments]

    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')  # Get selected student ids
        for student_id in student_ids:
            student = User.query.get(student_id)
            if student:
                enrollment = Enrollment(user_id=student.id, assignment_id=assignment.id)
                db.session.add(enrollment)
        db.session.commit()
        flash(f"Students added to {assignment.title} successfully!", "success")
        return redirect(url_for('view_assignment', assignment_id=assignment.id))

    return render_template('add_students_to_assignment.html', assignment=assignment, available_students=available_students)


@app.route('/teacher/insights/<int:assignment_id>')
@login_required
def view_teacher_insights(assignment_id):
    # Ensure the user is a teacher
    if current_user.role != 'Teacher':
        flash("Access denied. Only teachers can view this page.", "danger")
        return redirect(url_for('teacher_dashboard'))

    # Fetch the assignment
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        flash("Assignment not found.", "warning")
        return redirect(url_for('teacher_dashboard'))

    # Fetch the heatmap path
    heatmap_file = f'heatmap_assignment_{assignment_id}.png'
    heatmap_path = os.path.join('static', 'teacher_heatmaps', heatmap_file)

    # Verify if heatmap exists
    if not os.path.exists(heatmap_path):
        flash("Heatmap not found for this assignment.", "warning")
        return redirect(url_for('teacher_dashboard'))

    # Render the insights page
    return render_template(
        'teacher_insights.html',
        assignment=assignment,
        heatmap_file=heatmap_file,
        insights=assignment.insights
    )


## Admin dashboard routes and methods
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))  # Redirect to login if not admin

    # Redirect to the /admin page directly
    return redirect(url_for('admin.index'))


@app.route('/save_focus_data', methods=['POST'])
@login_required
def save_focus_data():
    data = request.json

    # Handle ISO 8601 timestamp with 'Z'
    timestamp_str = data['timestamp'].replace('Z', '+00:00')
    timestamp = datetime.fromisoformat(timestamp_str)

    focus_data = FocusData(
        user_id=current_user.id,
        assignment_id=data['assignment_id'],
        x_coord=data['x'],
        y_coord=data['y'],
        outside=data['outside'],
        timestamp=timestamp
    )
    db.session.add(focus_data)
    db.session.commit()
    print("Focus data saved successfully!")
    return jsonify({"message": "Focus data saved successfully!"})

@app.route('/student/heatmap/<int:assignment_id>')
@login_required
def heatmap(assignment_id):
    # Fetch focus data for the user and assignment
    focus_data = FocusData.query.filter_by(user_id=current_user.id, assignment_id=assignment_id).all()
    if not focus_data:
        return "No focus data available for this assignment.", 404

    # Fetch assignment details
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return "Assignment not found.", 404

    # Extract x and y coordinates
    x_coords = [data.x_coord for data in focus_data]
    y_coords = [data.y_coord for data in focus_data]

    # Save heatmap with user_id and assignment_id
    heatmap_dir = os.path.join('static', 'heatmaps')
    os.makedirs(heatmap_dir, exist_ok=True)
    file_name = f'heatmap_user_{current_user.id}_assignment_{assignment_id}.png'
    heatmap_path = os.path.join(heatmap_dir, file_name)

    plt.figure(figsize=(10, 8))
    plt.hist2d(x_coords, y_coords, bins=50, cmap='hot')
    plt.colorbar(label='Frequency')
    plt.title(f'Heatmap for {current_user.username} - {assignment.title}')
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.savefig(heatmap_path)
    plt.close()

    # Pass the file name, student name, and assignment title to the template
    return render_template(
        'heatmap.html',
        heatmap_file=file_name,
        student_name=current_user.username,
        assignment_title=assignment.title
    )

@app.route('/student/heatmaps')
@login_required
def all_heatmaps():
    # Define the directory for heatmaps
    heatmap_dir = os.path.join('static', 'heatmaps')
    os.makedirs(heatmap_dir, exist_ok=True)

    # Fetch all assignments the user is enrolled in
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    assignments = [enrollment.assignment for enrollment in enrollments]

    # Prepare the list of heatmaps
    heatmaps = []
    for assignment in assignments:
        file_name = f'heatmap_user_{current_user.id}_assignment_{assignment.id}.png'
        heatmap_path = os.path.join(heatmap_dir, file_name)

        # Check if the heatmap file exists
        if os.path.exists(heatmap_path):
            # Check the file's last modified time
            last_modified_time = datetime.fromtimestamp(os.path.getmtime(heatmap_path))
            if last_modified_time > datetime.utcnow() - timedelta(minutes=10):
                heatmaps.append({
                    'assignment_title': assignment.title,
                    'heatmap_file': file_name
                })
                continue

        # If the file doesn't exist or is outdated, generate the heatmap
        focus_data = FocusData.query.filter_by(user_id=current_user.id, assignment_id=assignment.id).all()
        if focus_data:
            x_coords = [data.x_coord for data in focus_data]
            y_coords = [data.y_coord for data in focus_data]

            plt.figure(figsize=(10, 8))
            plt.hist2d(x_coords, y_coords, bins=50, cmap='hot')
            plt.colorbar(label='Frequency')
            plt.title(f'Heatmap for {current_user.username} - {assignment.title}')
            plt.xlabel('X Coordinate')
            plt.ylabel('Y Coordinate')
            plt.savefig(heatmap_path)
            plt.close()

            # Add the heatmap to the list
            heatmaps.append({
                'assignment_title': assignment.title,
                'heatmap_file': file_name
            })

    # If no heatmaps exist, show a message
    if not heatmaps:
        flash("No focus data available for any assignments.", "warning")
        return redirect(url_for('student_dashboard'))

    # Render the heatmaps in the template
    return render_template(
        'students_all_heatmap.html',
        student_name=current_user.username,
        heatmaps=heatmaps
    )

@app.route('/teacher/heatmap/<int:assignment_id>')
@login_required
def teacher_assignment_heatmap(assignment_id):
    # Ensure the current user is a teacher
    if current_user.role != 'Teacher':
        flash("Access denied. Only teachers can view this page.", "danger")
        return redirect(url_for('login'))

    # Fetch assignment details
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        flash("Assignment not found.", "warning")
        return redirect(url_for('teacher_dashboard'))

    # Check if the current user is the owner of the assignment
    if assignment.teacher_id != current_user.id:
        flash("You do not have permission to view this heatmap.", "danger")
        return redirect(url_for('teacher_dashboard'))

    # Fetch all students enrolled in the assignment
    enrollments = Enrollment.query.filter_by(assignment_id=assignment_id).all()
    if not enrollments:
        flash("No students are enrolled in this assignment.", "warning")
        return redirect(url_for('teacher_dashboard'))

    # File naming: Use assignment_id and teacher_id
    heatmap_dir = os.path.join('static', 'teacher_heatmaps')
    os.makedirs(heatmap_dir, exist_ok=True)
    file_name = f'heatmap_assignment_{assignment_id}_teacher_{current_user.id}.png'
    heatmap_path = os.path.join(heatmap_dir, file_name)

    # Check if the heatmap already exists or needs to be regenerated
    if not os.path.exists(heatmap_path):
        # Generate a combined heatmap for all students
        x_coords = []
        y_coords = []
        for enrollment in enrollments:
            student_focus_data = FocusData.query.filter_by(user_id=enrollment.user_id, assignment_id=assignment_id).all()
            x_coords.extend([data.x_coord for data in student_focus_data])
            y_coords.extend([data.y_coord for data in student_focus_data])

        # Generate the heatmap if there is data
        if x_coords and y_coords:
            plt.figure(figsize=(10, 8))
            plt.hist2d(x_coords, y_coords, bins=50, cmap='hot')
            plt.colorbar(label='Frequency')
            plt.title(f'Heatmap for Assignment {assignment.title} (Generated by Teacher {current_user.username})')
            plt.xlabel('X Coordinate')
            plt.ylabel('Y Coordinate')
            plt.savefig(heatmap_path)
            plt.close()
        else:
            flash("No focus data available for this assignment.", "warning")
            return redirect(url_for('teacher_dashboard'))

    # Render the templatea
    return render_template(
        'teacher_heatmap.html',
        assignment_title=assignment.title,
        heatmap_file=file_name
    )


def calculate_distraction_time(data):
    """
    Calculate the total distraction time from focus data.
    """
    distraction_time = timedelta(0)
    previous_time = None

    for entry in data:
        if entry.outside:
            if previous_time:
                distraction_time += entry.timestamp - previous_time
        previous_time = entry.timestamp

    return distraction_time.total_seconds()  # Return in seconds


def calculate_focus_time(data, total_duration):
    """
    Calculate the total focus time from focus data.
    """
    distraction_time = calculate_distraction_time(data)
    focus_time = total_duration - distraction_time
    return focus_time

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


