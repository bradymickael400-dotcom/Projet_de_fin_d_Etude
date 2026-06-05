from flask import Blueprint, render_template, jsonify

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    return render_template("index.html")

# @main_bp.route("/api/hello")
# def hello_api():
#     return jsonify({"message": "Hello depuis Flask API"})
