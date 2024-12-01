from werkzeug.security import generate_password_hash
from models import db, User
from app import create_app

app = create_app()

# Create a superuser function
def create_superuser():
    with app.app_context():

        # Prompt for superuser credentials
        username = input("Enter superuser username: ")
        password = input("Enter superuser password: ")

        # Create a new superuser
        new_admin = User(
            username=username,
            password=generate_password_hash(password),
            role='Admin'
        )

        # Save the superuser to the database
        db.session.add(new_admin)
        db.session.commit()
        print(f"Superuser '{username}' created successfully!")

if __name__ == "__main__":
    create_superuser()
