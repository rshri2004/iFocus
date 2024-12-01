from flask_login import current_user
from flask import redirect, url_for, request, flash
from flask_admin import AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import func
from wtforms import SelectField, StringField, PasswordField
from models import db, User, Assignment, Note  # Import your models


class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'Admin'

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))


class UserAdminView(MyModelView):
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True

    column_list = ['id', 'username', 'role']
    column_searchable_list = ['username', 'role']
    column_exclude_list = ['password']  # Exclude password from being displayed

    # Form configuration
    form_columns = ['username', 'password', 'role']  # Specify form fields
    form_excluded_columns = ['password']  # Exclude the password from list view, not form

    # Define ALL form fields explicitly
    form_extra_fields = {
        'username': StringField('Username'),
        'password': PasswordField('Password'),
        'role': SelectField('Role', choices=[
            ('Student', 'Student'),
            ('Teacher', 'Teacher')
        ])
    }

    def get_query(self):
        """Override get_query to filter out Admin users from the list"""
        return self.session.query(self.model).filter(self.model.role != 'Admin')

    def get_count_query(self):
        """Override get_count_query to return a proper query object"""
        return self.session.query(func.count('*')).select_from(self.model).filter(self.model.role != 'Admin')

    # Override the create_model method to hash the password
    def create_model(self, form):
        model = self.model()
        existing_user = model.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash(f"User {existing_user.username} already exists!", "danger")
            return False

        model.username = form.username.data
        model.set_password(form.password.data)  # Hash the password before saving
        model.role = form.role.data
        db.session.add(model)
        db.session.commit()
        return model

    # Override the update_model method to hash the password if changed
    def update_model(self, form, model):
        from models import db, Assignment
        if model.username != form.username.data:
            existing_user = model.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash(f"User {existing_user.username} already exists!", "danger")
                return False

                # Check if the user role is being changed
            if model.role != form.role.data:
                    # If role is changing to "Student"
                if form.role.data == "Teacher":
                        # Check if the user has any enrollments
                    if model.assignmnets:
                        flash('Cannot change role to Student as the user has existing assignments.', 'danger')
                        return False


        if form.password.data:
            model.set_password(form.password.data)  # Hash the password before saving
        model.username = form.username.data
        db.session.commit()
        return model

    def delete_model(self, model):
        try:
            # Delete the user's associated assignments
            assignments = db.session.query(Assignment).filter_by(teacher_id=model.id).all()

            for assignment in assignments:
                # The related notes and questions will automatically be deleted due to cascade
                db.session.delete(assignment)

            # Delete the user
            db.session.delete(model)
            db.session.commit()
            flash(f'User {model.username} and associated data deleted successfully.', 'success')

            return True

        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting user: {str(e)}', 'danger')
            return False

    def delete_models(self, ids):
        """
        Handles bulk deletion of users and associated data (assignments, notes, questions, choices).
        """
        try:
            if isinstance(ids, list):  # Bulk delete
                for user_id in ids:
                    user = self.session.query(self.model).get(user_id)
                    if user:
                        # Call delete_model for each user to ensure proper deletion of associated data
                        self.delete_model(user)
                flash(f'{len(ids)} users and their associated data deleted successfully.', 'success')
            else:  # Single delete
                user = self.session.query(self.model).get(ids)
                if user:
                    self.delete_model(user)
                    flash(f'User {user.username} deleted successfully', 'success')

            return True

        except Exception as e:
            db.session.rollback()
            flash(f'Error during bulk delete: {str(e)}', 'danger')
            return False


class AssignmentAdminView(MyModelView):
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True

    column_list = ['id', 'title', 'teacher_id', 'pdf_path', 'youtube_url']
    column_searchable_list = ['title', 'pdf_path']
    column_filters = ['teacher_id']
    form_columns = ['title', 'teacher_id', 'pdf_path','youtube_url']
    form_excluded_columns = []

    def get_query(self):
        """Override get_query to filter out Admin users from the list"""
        return self.session.query(self.model)

    def get_count_query(self):
        """Override get_count_query to return a proper query object"""
        return self.session.query(func.count('*')).select_from(self.model)

    def on_model_change(self, form, model, is_created):
        if model.pdf_path and model.youtube_url:
            raise ValueError("An assignment can only have either a PDF or a YouTube video, not both.")

    def delete_model(self, model):
        try:
            # Related notes and questions will automatically be deleted due to cascade
            db.session.delete(model)
            db.session.commit()
            flash(f'Assignment {model.title} deleted successfully.', 'success')
            return True
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting assignment: {str(e)}', 'danger')
            return False

    def delete_models(self, ids):
        try:
            if isinstance(ids, list):  # Bulk delete
                for assignment_id in ids:
                    assignment = self.session.query(self.model).get(assignment_id)
                    if assignment:
                        self.delete_model(assignment)
                flash(f'{len(ids)} assignments and their associated data deleted successfully.', 'success')
            else:  # Single delete
                assignment = self.session.query(self.model).get(ids)
                if assignment:
                    self.delete_model(assignment)
                    flash(f'Assignment {assignment.title} deleted successfully', 'success')
            return True
        except Exception as e:
            db.session.rollback()
            flash(f'Error during bulk delete: {str(e)}', 'danger')
            return False


class NoteAdminView(MyModelView):
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True

    column_list = ['id', 'user_id', 'assignment_id', 'text']
    column_searchable_list = ['text']
    column_filters = ['user_id', 'assignment_id']
    form_columns = ['user_id', 'assignment_id', 'text']
    form_excluded_columns = []

    def get_query(self):
        """Override get_query to filter out Admin users from the list"""
        return self.session.query(self.model)

    def get_count_query(self):
        """Override get_count_query to return a proper query object"""
        return self.session.query(func.count('*')).select_from(self.model)

    def delete_model(self, model):
        try:
            db.session.delete(model)
            db.session.commit()
            flash(f'Note deleted successfully.', 'success')
            return True
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting note: {str(e)}', 'danger')
            return False

    def delete_models(self, ids):
        try:
            if isinstance(ids, list):  # Bulk delete
                for note_id in ids:
                    note = self.session.query(self.model).get(note_id)
                    if note:
                        self.delete_model(note)
                flash(f'{len(ids)} notes deleted successfully.', 'success')
            else:  # Single delete
                note = self.session.query(self.model).get(ids)
                if note:
                    self.delete_model(note)
                    flash(f'Note deleted successfully', 'success')
            return True
        except Exception as e:
            db.session.rollback()
            flash(f'Error during bulk delete: {str(e)}', 'danger')
            return False


class SignoutView(BaseView):
    @expose('/')
    def index(self):
        return redirect(url_for('logout'))