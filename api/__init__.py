"""API package containing Flask Blueprints for all system domains."""
from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Sub-blueprints will be registered inside app.py or api package
