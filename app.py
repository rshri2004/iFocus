from flask import Flask, Blueprint
from flask_login import LoginManager
from flask_admin import Admin
from models import DB_NAME, db, User, Assignment, Note
from flask_migrate import Migrate


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "secret_key"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_NAME}"

    db.init_app(app)
    with app.app_context():
        db.create_all()

    return app


app = create_app()
# migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from views import UserAdminView, AssignmentAdminView, NoteAdminView, SignoutView

admin = Admin(app, name='iFocus Admin', template_mode='bootstrap4')
admin.add_view(UserAdminView(User, db.session))
admin.add_view(AssignmentAdminView(Assignment, db.session))
admin.add_view(NoteAdminView(Note, db.session))
admin.add_view(SignoutView(name="Signout"))

from routes import *

if __name__ == '__main__':
    app.run(debug=True)
