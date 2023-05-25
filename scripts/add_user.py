#!/usr/bin/python

from werkzeug.security import generate_password_hash
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pwinput import pwinput
import sys


def main():
    # Connect to the DB
    collection = MongoClient()["coyote"]["users"]

    # Ask for data to store
    user = input("Enter your username: ")
    user_obj = collection.find_one({"_id": user})
    user_exits = user_obj is not None
    if not user_exits:
        password = pwinput(prompt="Enter your password: ")
        grp_string = input("Enter groups: ")
        fullname = input("Full name: ")
        pass_hash = generate_password_hash(password, method="pbkdf2:sha256")

    else:
        task_groups = input(
            "Do you want to add groups for the user (add/remove/none): "
        )

        if task_groups.lower() in ["add", "remove"]:
            grp_string = input("Enter groups: ")
        else:
            sys.exit("Bye...")

    grp_arr = grp_string.split(",")

    # Insert the user in the DB or Update the groups for existing users

    try:
        if not user_exits:
            collection.insert_one(
                {
                    "_id": user,
                    "password": pass_hash,
                    "groups": grp_arr,
                    "fullname": fullname,
                }
            )
            print("User created.")
        elif task_groups.lower() == "add":
            existing_groups = user_obj["groups"]
            existing_groups.extend(grp_arr)
            new_groups = list(set(existing_groups))

            collection.find_one_and_update(
                {"_id": user},
                {
                    "$set": {
                        "groups": new_groups,
                    },
                },
            )
            print("User updated.")
        elif task_groups.lower() == "remove":
            existing_groups = user_obj["groups"]
            new_groups = [g for g in existing_groups if g not in grp_arr]

            collection.find_one_and_update(
                {"_id": user},
                {
                    "$set": {
                        "groups": new_groups,
                    },
                },
            )
            print("User updated.")
    except PyMongoError as e:
        print(f"Operation Failed due to {str(e)}")


if __name__ == "__main__":
    main()
