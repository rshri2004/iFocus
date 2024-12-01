import os
from app import app, db
from routes import process_pdf, fetch_youtube_transcription
from models import User, Assignment, Enrollment
from werkzeug.security import generate_password_hash

def create_users():
    """
    Create teacher t1 and students s1, s2 with specified passwords.
    """
    # Create teacher t1
    teacher1 = User(username="t1", password=generate_password_hash("t1"), role="Teacher")
    teacher2 = User(username="t2", password=generate_password_hash("t2"), role="Teacher")
    db.session.add(teacher1)
    db.session.add(teacher2)

    # Create students s1 and s2
    student1 = User(username="s1", password=generate_password_hash("s1"), role="Student")
    student2 = User(username="s2", password=generate_password_hash("s2"), role="Student")
    db.session.add(student1)
    db.session.add(student2)

    db.session.commit()
    print("Users created: t1 (teacher), t2 (teacher), s1 (student), s2 (student)")

def create_assignments():
    """
    Create assignments by teacher t1 and assign them to students s1 and s2.
    """
    # Retrieve teacher and students
    teacher1 = User.query.filter_by(username="t1").first()
    teacher2 = User.query.filter_by(username="t2").first()
    student1 = User.query.filter_by(username="s1").first()
    student2 = User.query.filter_by(username="s2").first()

    if not teacher1 or not teacher2 or not student1 or not student2:
        print("Users are not created yet. Run create_users() first.")
        return

     # Ensure the static folder path for the PDF file
    static_folder = os.path.join(app.root_path, "static", "uploads", "pdfs")
    print(static_folder)
    os.makedirs(static_folder, exist_ok=True)

    # Copy the PDF file to the static folder
    source_pdf = os.path.expanduser("~/Downloads/AI.pdf")
    dest_pdf = os.path.join(static_folder, "AI.pdf")

    if not os.path.exists(source_pdf):
        print(f"File not found: {source_pdf}")
        return
    else:
        # Copy the file to the static/uploads folder
        if not os.path.exists(dest_pdf):
            with open(source_pdf, "rb") as src, open(dest_pdf, "wb") as dst:
                dst.write(src.read())
        print(f"PDF copied to: {dest_pdf}")

    # Create assignment1 with a PDF
    assignment1_summary = process_pdf(dest_pdf)
    assignment1 = Assignment(
        title="Assignment 1 PDF",
        pdf_path=dest_pdf,
        youtube_url=None,
        teacher_id=teacher1.id,
        summary=assignment1_summary
    )
    db.session.add(assignment1)

    # Create assignment2 with a YouTube link
    youtube_url = "https://www.youtube.com/watch?v=F7AK-WzpYdY&t=5s"
    assignment2_summary = fetch_youtube_transcription(youtube_url)
    assignment2 = Assignment(
        title="Assignment 2 Video",
        pdf_path=None,
        youtube_url=youtube_url,
        teacher_id=teacher1.id,
        summary=assignment2_summary
    )
    db.session.add(assignment2)

    # Create assignment1 with a PDF
    assignment3_summary = process_pdf(dest_pdf)
    assignment3 = Assignment(
        title="Assignment 3 PDF",
        pdf_path=dest_pdf,
        youtube_url=None,
        teacher_id=teacher2.id,
        summary=assignment3_summary
    )
    db.session.add(assignment3)

    # Create assignment2 with a YouTube link
    youtube_url = "https://www.youtube.com/watch?v=F7AK-WzpYdY&t=5s"
    assignment4_summary = fetch_youtube_transcription(youtube_url)
    assignment4 = Assignment(
        title="Assignment 2 Video",
        pdf_path=None,
        youtube_url=youtube_url,
        teacher_id=teacher2.id,
        summary=assignment4_summary
    )
    db.session.add(assignment4)

    db.session.commit()
    print("Assignments created: Assignment 1 (PDF), Assignment 2 (YouTube link)")

    # Assign both assignments to students
    for assignment in [assignment1, assignment2, assignment3, assignment4]:
        db.session.add(Enrollment(assignment_id=assignment.id, user_id=student1.id))
        db.session.add(Enrollment(assignment_id=assignment.id, user_id=student2.id))

    db.session.commit()
    print("Assignments assigned to students s1 and s2")

if __name__ == "__main__":
    with app.app_context():
        print("Creating users...")
        create_users()

        print("Creating assignments...")
        create_assignments()

        print("Data creation completed!")
