"""Login page routes, login_mangager funcs and User class"""

from typing import List
from flask_wtf import FlaskForm

from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    EmailField,
    HiddenField,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    Regexp,
    Email,
    ValidationError,
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app as cll_app
from cll_genie.extensions import mongo


# User class:
class User:
    def __init__(self, username: str, groups: List[str], fullname: str):
        self.username = username
        self.groups = groups
        self.fullname = fullname

    def is_authenticated(self) -> bool:
        return True

    def is_active(self) -> bool:
        return True

    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return self.username

    def get_fullname(self) -> str:
        return self.fullname

    def get_groups(self) -> List[str]:
        return self.groups

    def super_user_mode(self) -> bool:
        """
        Check is current user allowed to edit/delete data from samples and results

        Permissions are defined through user-groups listed in
        'CLL_GENIE_SUPER_PERMISSION_GROUPS' in config.py
        """

        user_groups = self.get_groups()
        permitted_groups = cll_app.config["CLL_GENIE_SUPER_PERMISSION_GROUPS"]
        cll_app.logger.debug(f"User in groups: {user_groups}")
        cll_app.logger.debug(f"Permitted groups: {permitted_groups}")

        permission_granted = False

        for group in user_groups:
            if group in permitted_groups:
                permission_granted = True
                cll_app.logger.info("Permission granted!")
                break

        if not permission_granted:
            cll_app.logger.warning(
                "User is not authorized to modify data based on group policy."
            )

        if cll_app.debug:
            cll_app.logger.debug("DEBUG mode ON. Authorizing sample edit.")
            permission_granted = True

        return permission_granted

    def admin(self) -> bool:
        """
        Check if current user is admin
        """

        user_groups = self.get_groups()

        admin = False

        if "admin" in user_groups or "lymphotrack_admin" in user_groups:
            admin = True
            cll_app.logger.info("Admin rights granted for the user!")

        else:
            cll_app.logger.warning("Admin rights declined for the user.")

        if cll_app.debug:
            cll_app.logger.debug("DEBUG mode ON. Authorizing sample edit.")
            admin = True

        return admin

    @staticmethod
    def validate_login(password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)


# LoginForm
class LoginForm(FlaskForm):
    """Login form"""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class UpdateUser:
    def __init__(
        self, user=None, password=None, groups=None, fullname=None, email=None
    ):
        self.user = user
        self.password = password
        self.groups = groups
        self.fullname = fullname
        self.email = email
        self.users_collection = mongo.cx["coyote"]["users"]

    def user_exists(self):
        return self.users_collection.find_one({"_id": self.user}) is not None

    def get_username(self):
        return self.user

    def get_user_data(self):
        return self.users_collection.find_one({"_id": self.user})

    def get_groups(self):
        return self.users_collection.find_one({"_id": self.user}).get("groups", [])

    def update_user_details(self, form_data):
        user_data = self.get_user_data()
        new_email = form_data.get("email", "")
        new_fullname = form_data.get("fullname", "")
        add_groups = form_data.get("add_groups", "").split(",")
        remove_groups = form_data.get("remove_groups", "").split(",")

        if user_data:
            current_email = user_data.get("email", "")
            current_fullname = user_data.get("fullname", "")
            current_groups = self.get_groups()
            current_groups.extend(add_groups)
            groups = list(set(current_groups))

            for group in remove_groups:
                if group in groups:
                    groups.remove(group)
            self.users_collection.find_one_and_update(
                {"_id": self.user},
                {
                    "$set": {
                        "email": (
                            new_email
                            if new_email != current_email or new_email is not None
                            else current_email
                        ),
                        "fullname": (
                            new_fullname
                            if new_fullname != current_fullname
                            or new_fullname is not None
                            else current_fullname
                        ),
                        "groups": groups,
                    }
                },
            )
            return True
        else:
            return False

    def add_user(self):
        try:
            self.users_collection.insert_one(
                {
                    "_id": self.user,
                    "password": generate_password_hash(
                        self.password, method="pbkdf2:sha256"
                    ),
                    "groups": self.groups,
                    "fullname": self.fullname,
                    "email": self.email,
                }
            )
            return True
        except:
            return False

    def update_password(self, new_password):
        try:
            pass_hash = generate_password_hash(new_password, method="pbkdf2:sha256")
            self.users_collection.find_one_and_update(
                {"_id": self.user},
                {
                    "$set": {
                        "password": pass_hash,
                    }
                },
            )
            return True
        except:
            return False

    def update_email(self):
        try:
            self.users_collection.find_one_and_update(
                {"_id": self.user},
                {
                    "$set": {
                        "email": self.email,
                    }
                },
            )
            return True
        except:
            return False


def validate_username(form, field):
    user_data = UpdateUser(user=field.data)
    user_exists = user_data.user_exists()
    if user_exists:
        raise ValidationError("User already exists. Please choose another username.")


class UserForm(FlaskForm):
    """User form with enhanced password validation and email validation."""

    username = StringField(
        "User Name",
        validators=[
            DataRequired(message="User Name is required."),
            validate_username,
        ],
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Invalid email address."),
        ],
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, message="Password must be at least 8 characters long."),
            Regexp(
                r"^.*(?=.*\d)(?=.*[a-zA-Z]).*$",
                message="Password must contain both letters and numbers.",
            ),
            EqualTo("confirm_password", message="Passwords must match."),
        ],
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(message="Please confirm your password.")],
    )

    fullname = StringField(
        "Full Name", validators=[DataRequired(message="Full Name is required.")]
    )

    lymphotrack = BooleanField("lymphotrack")
    lymphotrack_admin = BooleanField("lymphotrack_admin")


class SearchUserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    submit = SubmitField("Search")


class EditUserForm(FlaskForm):
    user_id = HiddenField("User ID")
    fullname = StringField("Full Name", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired()])
    groups = StringField("Current Groups")
    add_groups = StringField("Add Groups (comma separated)")
    remove_groups = StringField("Remove Groups (comma separated)")
    save = SubmitField("Save Changes", render_kw={"class": "btn btn-primary"})
