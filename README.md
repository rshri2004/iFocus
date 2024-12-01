# iFocus Application

iFocus is a Flask-based web application designed to monitor student focus and engagement using eye-tracking data. It allows teachers to create assignments, analyze student focus patterns, and generate insights through OpenAI GPT models.

---

## Features

### For Students
- **Dashboard**: View assigned tasks and access insights about their focus performance.
- **Heatmaps**: Visual representation of focus patterns for assignments.
- **Insights**: Personalized feedback on focus and suggestions for improvement.

### For Teachers
- **Create Assignments**: Upload assignments as PDFs or provide YouTube video links.
- **Monitor Engagement**: Access aggregated heatmaps and insights for all students in an assignment.

### For Admins
- **Admin Dashboard**: Manage Users, Assignments, Enrollment, and view analytics.

---

## Setup

### Prerequisites
- Python 3.10 or above
- Virtual environment (recommended)
- OpenAI API Key

### Installation
1. **Clone the Repository**:
```bash
   git clone git@github.com:SchertzS/iFocus.git 
   cd iFocus
```

### Set Up Virtual Environment
```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   venv\\Scripts\\activate     # On Windows
```

### Install Dependencies
```bash
  pip install -r requirements.txt
```
### Set Up Environment Variables
```bash
  OPENAI_API_KEY=your_openai_api_key
  FLASK_APP=app.py
  FLASK_ENV=development
  LLM_MODEL="openai" or "llama" (default will be openai if its not set)
```

### Running the application
```bash
   flask --app app run
   or run from pycharm
```
The application will be available at https://127.0.0.1:443.

---

### Creating Test data

#### Create a Superuser:
```bash
   python create_superuser.py
```
#### Creating Teacher and Students
```bash
   python create_data.py
```
Creates teacher t1 with password t1, and students s1/s1 and s2/s2

---

## Usage
### For Students:
- **Signup as new Student**
- **Log in using your credentials**
- **View your assignments**
- **Write notes and Save notes**
- **View Insights about your Focus data**

### For Teacher:
- **Signup as new Teacher**
- **Log in using your credentials**
- **Create new assignments**
- **View your assignments**
- **Add Students to  your assignments**
- **View Insights about your assigments based student's focus data**

### Admins
- **Run nighlty cron jobs to generate insights for students and assignments**

---

### Cron Job
#### Manual run
```bash
   python cron_job.py
```
#### Scheduled run
```bash
   crontab -e (opens the vi or other editor)
   type the following content and save to generate insights everyday night at 7pm
   * 19 * * * cd /Users/shri/workspace/HCI/final_project/iFocus && source env/bin/activate && python iFocus/cron_job.py >> ./cron_job.log 2>&1
   crontab -l (review the existing cron jobs)
```

---

## Project Structure
- **iFocus**: Top level project directory
  - **env**: Python virtual environment 
  - **iFocus**: Flask app top-lvel directory
    - **app.py**: Initializes the Flask application.
    - **models.py**: Defines the database schema for users, assignments, enrollments, focus data, etc.
    - **routes.py**: Handles application routing and logic for students and teachers.
    - **views.py**: Manage database model views for the Admin user
    - **cron_job.py**: Automates heatmap generation and insights computation.
    - **cron_utils.py**: Utility functions for heatmap analysis and insights generation.
    - **create_superuser.py**: Utility to create a superuser.
    - **create_data.py**: Seeds the database with initial data.
    - **requirements.txt**: List of dependencies.
    - **templates**: Directory that has all the frontend HTML templates
    - **static**: Directory for storing styles, uploaded pdfs, and generated heatmaps
    - **instance**: Directory that stores the iFocus sqlite database

---

## LLM Integration
The application can either leverage Llma3.2 or  OpenAI's GPT-4 model for generating insights about focus patterns:

- **Student Insights**: Personalized focus feedback.
- **Teacher Insights**: Aggregated insights for assignment-level analysis.


## Thirdparty libraries Used
- **Flask**: web application development.
- **OpenAI**: providing powerful language models.
- **Bootstrap**: responsive UI components.
- **WebGazer**: WebGazer for tracking user focus
