# login_bp dependencies
from flask import current_app as cll_genie  # type: ignore
from flask import request, render_template, redirect, url_for, flash  # type: ignore
from flask_login import login_required, login_user, logout_user, current_user  # type: ignore

from cll_genie.extensions import login_manager, mongo
from cll_genie.blueprints.login import login_bp
from cll_genie.blueprints.login.login import LoginForm, User


# Login routes:


@login_bp.route("/login/", methods=["GET", "POST"])
def login():
    if not current_user.is_authenticated:
        form = LoginForm()

        if request.method == "POST" and form.validate_on_submit():
            users_collection = mongo.cx["coyote"]["users"]
            user = users_collection.find_one({"_id": form.username.data})
            if user and User.validate_login(user["password"], form.password.data):
                user_obj = User(
                    user["_id"], user["groups"], user["fullname"] or user["_id"]
                )
                login_user(user_obj)
                cll_genie.logger.info(f"Logged in user: {user['fullname']}")
                flash(f"Logged in user: {user['fullname']}", "success")
                return redirect(
                    request.args.get("next") or url_for("main_bp.cll_genie")
                )
            else:
                cll_genie.logger.warning(f"Login failed for user: {form.username.data}")
                flash(f"Login failed for user: {form.username.data}", "error")

        return render_template("login.html", title="login", form=form)
    else:
        return redirect(url_for("main_bp.cll_genie"))


@login_bp.route("/logout/")
@login_required
def logout():
    logout_user()
    flash(f"Logged out successfully", "success")
    return redirect(url_for("login_bp.login"))


@login_manager.user_loader
def load_user(username):
    users_collection = mongo.cx["coyote"]["users"]
    user = users_collection.find_one({"_id": username})
    if not user:
        return None
    return User(
        user["_id"],
        user["groups"],
        user["fullname"] if "fullname" in user else user["_id"],
    )
