"""
Configuration settings for Emergency Ambulance Dispatch & Hospital Recommendation System.
Supports environment-based configuration for SQLite (default) or MySQL.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "medroute-emergency-dispatch-secret-key-2026")
    
    # Database configuration: defaults to SQLite inside project directory
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'emergency_dispatch.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Recommendation Scoring Weights (configurable defaults)
    # Formula: Score = W_DIST * S_dist + W_TRAFFIC * S_traffic + W_BEDS * S_beds + W_SPEC * S_spec
    WEIGHT_DISTANCE = float(os.environ.get("WEIGHT_DISTANCE", 0.40))
    WEIGHT_TRAFFIC = float(os.environ.get("WEIGHT_TRAFFIC", 0.30))
    WEIGHT_BEDS = float(os.environ.get("WEIGHT_BEDS", 0.20))
    WEIGHT_SPECIALIZATION = float(os.environ.get("WEIGHT_SPECIALIZATION", 0.10))
    
    # Average speed assumption for travel time calculation (km/h) when edge time is not specified
    DEFAULT_AMBULANCE_SPEED_KMH = float(os.environ.get("DEFAULT_AMBULANCE_SPEED_KMH", 45.0))
    
    # Traffic multipliers for travel time
    TRAFFIC_MULTIPLIERS = {
        "LOW": 1.0,
        "MEDIUM": 1.4,
        "HIGH": 2.0
    }


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
