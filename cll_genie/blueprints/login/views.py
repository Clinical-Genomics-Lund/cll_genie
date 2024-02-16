# login_bp dependencies
from flask import current_app as cll_app  # type: ignore
from flask import request, render_template, redirect, url_for, flash, abort  # type: ignore
from flask_login import login_required, login_user, logout_user, current_user  # type: ignore

from cll_genie.extensions import login_manager, mongo
from cll_genie.blueprints.login import login_bp
from cll_genie.blueprints.main import main_bp
from cll_genie.blueprints.login.login import (
    LoginForm,
    User,
    UserForm,
    UpdateUser,
    SearchUserForm,
    EditUserForm,
)


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
                cll_app.logger.info(f"Logged in user: {user['fullname']}")
                flash(f"Logged in user: {user['fullname']}", "success")
                return redirect(
                    request.args.get("next") or url_for("main_bp.cll_genie")
                )
            else:
                cll_app.logger.warning(f"Login failed for user: {form.username.data}")
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


@login_bp.route("/add_user/", methods=["GET", "POST"])
@login_required
def add_user():
    if not current_user.admin():
        abort(403)

    form = UserForm()
    if form.validate_on_submit():
        groups = []
        if form.lymphotrack.data:
            groups.append("lymphotrack")

        if form.lymphotrack_admin.data:
            groups.append("lymphotrack_admin")

        user_obj = UpdateUser(
            form.username.data,
            form.password.data,
            groups,
            form.fullname.data,
            form.email.data,
        )

        if user_obj.add_user():
            flash("User added successfully!", "success")
            return redirect(url_for("main_bp.add_user"))
        else:
            flash("User not added!", "error")

    return render_template("add_user.html", title="Add User", form=form)


@login_bp.route("/update_user/", methods=["GET", "POST"])
def update_user():
    if not current_user.admin():
        abort(403)

    search_form = SearchUserForm()
    edit_form = None  # Initialize edit_form as None
    user_found = False

    if search_form.validate_on_submit() and search_form.submit.data:
        username = search_form.username.data
        user_obj = UpdateUser(user=username)
        user_found = user_obj.user_exists()

        if user_found:
            user_data = user_obj.get_user_data()
            edit_form = EditUserForm()
            edit_form.user_id.data = user_obj.get_username()
            edit_form.fullname.data = user_data.get("fullname", "")
            edit_form.email.data = user_data.get("email", "")
            edit_form.groups.data = ", ".join(user_data.get("groups", ""))
        else:
            pass

    if not user_found:
        edit_form = EditUserForm()

    if edit_form.validate_on_submit() and edit_form.save.data:
        edit_user_obj = UpdateUser(user=edit_form.user_id.data)
        success = edit_user_obj.update_user_details(edit_form.data)
        if success:
            flash("User details updated successfully.", "success")
            cll_app.logger.info(
                f"Details updated successfully for the user {edit_form.user_id.data}"
            )
            return redirect(url_for("main_bp.admin"))
        else:
            cll_app.logger.error(
                f"Failed to update user details for the user {edit_form.user_id.data}"
            )
            flash("Failed to update user details.", "danger")
    else:
        cll_app.logger.error(
            f"Form validation failed for the user {edit_form.user_id.data}\n{edit_form.errors}"
        )

    return render_template(
        "update_user.html",
        search_form=search_form,
        edit_form=edit_form,
        user_found=user_found,
    )


@login_bp.route("/remove_user/", methods=["GET", "POST"])
@login_required
def remove_user():
    if current_user.admin():
        return render_template("remove_user.html")
    else:
        abort(403)
