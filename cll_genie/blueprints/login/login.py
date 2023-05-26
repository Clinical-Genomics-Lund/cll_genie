"""Login page routes, login_mangager funcs and User class"""

from typing import List

# LoginForm dependencies
from flask_wtf import Form, FlaskForm  # type: ignore
from wtforms import StringField, PasswordField  # type: ignore
from wtforms.validators import DataRequired  # type: ignore

# User-class dependencies:
from werkzeug.security import check_password_hash

from flask import current_app as cll_app


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
                "User not authorized to modify data based on group policy."
            )

        if cll_app.debug:
            cll_app.logger.debug("DEBUG mode ON. Authorizing sample edit.")
            return True

        return permission_granted

    @staticmethod
    def validate_login(password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)


# LoginForm
class LoginForm(FlaskForm):
    """Login form"""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
