import os
import matplotlib.pyplot as plt
from app import db, create_app
from models import FocusData, Assignment, Enrollment
import openai
from openai import OpenAI
from cron_utils import summarize_focus_behavior
from langchain_ollama import ChatOllama


# Initialize OpenAI API key
openai.api_key = None
llm_model = os.getenv("LLM_MODEL", "openai").lower()
if llm_model == "openai":
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("The OPENAI_API_KEY environment variable is not set.")
    else:
        print("Generating insights using OpenAI Model")
else:
    print("Generating insights using Llama Model")

# Set up Flask application context
app = create_app()
app.app_context().push()

# Heatmap directory
project_root = os.path.abspath(os.path.dirname(__file__))
heatmap_dir = os.path.join(project_root, 'static', 'heatmaps')
teacher_heatmap_dir = os.path.join(project_root, 'static', 'teacher_heatmaps')

os.makedirs(heatmap_dir, exist_ok=True)

def aggregate_focus_data(assignment_id):
    """Aggregates focus data for all students in an assignment."""
    focus_data = FocusData.query.filter_by(assignment_id=assignment_id).all()
    if not focus_data:
        return None  # No focus data available

    x_coords = [data.x_coord for data in focus_data]
    y_coords = [data.y_coord for data in focus_data]

    return {"x_coords": x_coords, "y_coords": y_coords}

def generate_assignment_heatmap(assignment_id):
    """Generate a heatmap for all students in a given assignment."""
    # Aggregate focus data
    aggregated_data = aggregate_focus_data(assignment_id)
    if not aggregated_data:
        return None  # No focus data available

    # File naming convention
    file_name = f'heatmap_assignment_{assignment_id}.png'
    heatmap_path = os.path.join(teacher_heatmap_dir, file_name)

    # Generate heatmap
    plt.figure(figsize=(10, 8))
    plt.hist2d(aggregated_data["x_coords"], aggregated_data["y_coords"], bins=50, cmap='hot')
    plt.colorbar(label='Frequency')
    plt.title(f'Heatmap for Assignment {assignment_id}')
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.savefig(heatmap_path)
    plt.close()

    return heatmap_path

def generate_assignment_insights(assignment):
    """Generate insights for an assignment using aggregated focus data."""
    # Aggregate focus data for all students
    focus_data = FocusData.query.filter_by(assignment_id=assignment.id).all()
    if not focus_data:
        print(f"No focus data available for Assignment {assignment.id}.")
        return None

    # Summarize focus behavior using the utility function
    summary = summarize_focus_behavior(focus_data)
    if summary is None:
        print(f"Error generating insights for assignment Assignment {assignment.id}")
        return

    # Prepare a prompt for OpenAI
    prompt = (
        f"Analyze the following summary of focus behavior for Assignment '{assignment.title}':\n\n"
        f"{summary}\n\n"
        f"Based on this summary, provide actionable insights to help the teacher improve student engagement, "
        f"address potential distractions, and make the assignment more effective. Keep the insights concise and useful."
    )

    if llm_model == "llama":
        return generate_assignment_insights_llama(assignment, prompt)
    else:
        return generate_assignment_insights_openai(assignment, prompt)


def generate_assignment_insights_llama(assignment, prompt):
    """Generate insights for an assignment using aggregated focus data with Llama model"""
    messages = [
        (
            "system",
            "You are an assistant that provides actionable feedback for teachers based on student focus behavior data."
        ),
        ("human", prompt)
    ]
    try:
        llm = ChatOllama(
            model="llama3.2",
            temperature=0
        )

        ai_msg = llm.invoke(messages)
        return ai_msg.content
    except Exception as e:
        print(f"Error generating insights for Assignment {assignment.id}: {str(e)}")
        return None

def generate_assignment_insights_openai(assignment, prompt):
    """Generate insights for an assignment using aggregated focus data."""
    # Prepare a prompt for OpenAI

    # Call OpenAI to generate insights
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=openai.api_key)
        model = "gpt-4"
        messages = [
            {
                "role": "system",
                "content": "You are an assistant that provides actionable feedback for teachers "
                           "based on student focus behavior data."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        response = client.chat.completions.create(
            messages=messages,
            model=model,
        )
        insights = response.choices[0].message.content.strip()
        return insights
    except Exception as e:
        print(f"Error generating insights for Assignment {assignment.id}: {str(e)}")
        return None


def store_assignment_insights(assignment, insights):
    """Store the insights in the Assignment table."""
    #print(assignment, insights)
    if assignment:
        assignment.insights = insights
        db.session.commit()
    else:
        print(f"No assignment found with ID {assignment.id}")

def generate_insights_for_all_assignments():
    """Main function to generate heatmaps and insights for all assignments."""
    assignments = Assignment.query.all()
    for assignment in assignments:
        print(f"Processing Assignment {assignment.id}: {assignment.title}")
        # Generate heatmap
        heatmap_path = generate_assignment_heatmap(assignment.id)
        if heatmap_path:
            print(f"Heatmap generated: {heatmap_path}")
            # Generate insights
            insights = generate_assignment_insights(assignment)
            if insights:
                # Store insights in Assignment table
                store_assignment_insights(assignment, insights)
                print(f"Insights generated and stored successfully for Assignment {assignment.id}")
            else:
                print(f"Failed to generate insights for Assignment {assignment.id}")
        else:
            print(f"Failed to generate heatmap for Assignment {assignment.id}")


def generate_heatmap(student_id, assignment_id):
    """Generate a heatmap for a given student and assignment."""
    focus_data = FocusData.query.filter_by(user_id=student_id, assignment_id=assignment_id).all()
    if not focus_data:
        return None  # No focus data available

    # Extract x and y coordinates
    x_coords = [data.x_coord for data in focus_data]
    y_coords = [data.y_coord for data in focus_data]

    # File naming convention
    file_name = f'heatmap_user_{student_id}_assignment_{assignment_id}.png'
    heatmap_path = os.path.join(heatmap_dir, file_name)

    # Generate heatmap
    plt.figure(figsize=(10, 8))
    plt.hist2d(x_coords, y_coords, bins=50, cmap='hot')
    plt.colorbar(label='Frequency')
    plt.title(f'Heatmap for Student {student_id} - Assignment {assignment_id}')
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.savefig(heatmap_path)
    plt.close()

    return heatmap_path


def generate_insights(student, assignment):
    """Generate insights using OpenAI or Llama based on the heatmap."""
    # Simulate a description or summary of the heatmap as input text
    focus_data = FocusData.query.filter_by(user_id=student.id, assignment_id=assignment.id).all()
    summary = summarize_focus_behavior(focus_data)
    if summary is None:
        print(f"Error generating insights for Student {student.id}, Assignment {assignment.id}")
        return
    text = f"Please analyze the student {student.username}'s  focus behavior for the assigment {assignment.title} " \
           f"provied as {summary} and provide concise insights for student focus patterns."

    if llm_model == "llama":
        return generate_insights_llama(student, assignment, text)
    else:
        return generate_insights_openai(student, assignment, text)


def generate_insights_llama(student, assignment, text):
    """Generate insights using Llama based on the heatmap."""
    messages = [
        (
            "system",
            f"You are an assistant that reviews student's focus behavior for the given assignment {assignment.title}  "
            f"and student {student.username} and summarizes the into concise insights for student focus patterns."
            f"Based on your analysis, Maintain a personal tone and address directly to the student and "
            f"provide best suggestions for improving their focus and concentration and study patterns."
            f"Use the signature as Best Regards, Your friendly iFocus Buddy"
        ),
        ("human", f"Summarize in rich text format in 200 words :\n\n{text}")
    ]
    try:
        llm = ChatOllama(
            model="llama3.2",
            temperature=0
        )

        ai_msg = llm.invoke(messages)
        return ai_msg.content
    except Exception as e:
        print(f"Error generating insights: {str(e)}")
        return None

def generate_insights_openai(student, assignment, text):
    """Generate insights using OpenAI or Llama based on the heatmap."""
    client = OpenAI(api_key=openai.api_key)
    model = "gpt-4"
    messages = [
        {
            "role": "system",
            "content": f"You are an assistant that reviews student's focus behavior for the given assignment {assignment.title}  "
                       f"and student {student.username} and summarizes the into concise insights for student focus patterns."
                       f"Based on your analysis, Maintain a personal tone and address directly to the student and "
                       f"provide best suggestions for improving their focus and concentration and study patterns."
                       f"Use the signature as Best Regards, Your friendly iFocus Buddy"
        },
        {
            "role": "user",
            "content": f"Summarize in rich text format in 200 words :\n\n{text}"
        }
    ]
    try:
        response = client.chat.completions.create(
            messages=messages,
            model=model,
        )
        insights = response.choices[0].message.content
        return insights
    except Exception as e:
        print(f"Error generating insights: {str(e)}")
        return None

def store_insights(student_id, assignment_id, insights):
    """Store the insights in the Enrollment table."""
    enrollment = Enrollment.query.filter_by(user_id=student_id, assignment_id=assignment_id).first()
    if enrollment:
        enrollment.insights = insights
        db.session.commit()
    else:
        print(f"No enrollment found for student {student_id} and assignment {assignment_id}")

def generate_for_user(user_id):
    user_enrollments = Enrollment.query.filter_by(user_id=user_id).all()
    # Iterate through the user's enrollments
    for enrollment in user_enrollments:
        student_id = enrollment.user_id
        assignment_id = enrollment.assignment_id
        student = enrollment.user
        assignment = enrollment.assignment

        # Check if there is focus data
        focus_data = FocusData.query.filter_by(user_id=student_id, assignment_id=assignment_id).all()
        if focus_data:
            print(f"Processing Student {student_id}, Assignment {assignment_id}")
            # Generate heatmap
            heatmap_path = generate_heatmap(student_id, assignment_id)
            if heatmap_path:
                print(f"Heatmap generated: {heatmap_path}")
                # Generate insights
                insights = generate_insights(student, assignment)
                if insights:
                    # Store insights in Enrollment table
                    store_insights(student_id, assignment_id, insights)
                    print(f"Insights generated and stored successfully")
                else:
                    print(f"Failed to generate insights for Student {student_id}, Assignment {assignment_id}")
            else:
                print(f"Failed to generate heatmap for Student {student_id}, Assignment {assignment_id}")
        else:
            print(f"No focus data for Student {student_id}, Assignment {assignment_id}")


def generate_for_all_users():
    """Main function to check focus data, generate heatmaps, analyze, and store insights."""
    # Fetch all enrollments
    enrollments = Enrollment.query.all()

    for enrollment in enrollments:
        student_id = enrollment.user_id
        assignment_id = enrollment.assignment_id
        student = enrollment.user
        assignment = enrollment.assignment

        # Check if there is focus data
        focus_data = FocusData.query.filter_by(user_id=student_id, assignment_id=assignment_id).all()
        if focus_data:
            print(f"Processing Student {student_id}, Assignment {assignment_id}")
            # Generate heatmap
            heatmap_path = generate_heatmap(student_id, assignment_id)
            if heatmap_path:
                print(f"Heatmap generated: {heatmap_path}")
                # Generate insights
                insights = generate_insights(student, assignment)
                if insights:
                    # Store insights in Enrollment table
                    store_insights(student_id, assignment_id, insights)
                    print(f"Insights generated and stored successfully")
                else:
                    print(f"Failed to generate insights for Student {student_id}, Assignment {assignment_id}")
            else:
                print(f"Failed to generate heatmap for Student {student_id}, Assignment {assignment_id}")
        else:
            print(f"No focus data for Student {student_id}, Assignment {assignment_id}")


if __name__ == "__main__":
    print("\nGenerating insights for all the students:")
    generate_for_all_users()
    print("\nGenerating insights for all the assignments")
    generate_insights_for_all_assignments()