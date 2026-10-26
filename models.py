"""
SQLAlchemy database models for MedRoute Emergency Dispatch System.
Normalized entities: Hospitals, Specializations, Road Network (Nodes/Edges),
Ambulances, Emergency Requests, and Dispatch Results.
"""

from datetime import datetime, timezone
import json
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Table, Text, CheckConstraint
)
from sqlalchemy.orm import relationship
from database import Base

# Association table for Hospital <-> Specialization (Many-to-Many)
hospital_specializations = Table(
    "hospital_specializations",
    Base.metadata,
    Column("hospital_id", Integer, ForeignKey("hospitals.hospital_id", ondelete="CASCADE"), primary_key=True),
    Column("specialization_id", Integer, ForeignKey("specializations.specialization_id", ondelete="CASCADE"), primary_key=True)
)


class Specialization(Base):
    __tablename__ = "specializations"

    specialization_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    hospitals = relationship("Hospital", secondary=hospital_specializations, back_populates="specializations")

    def to_dict(self):
        return {
            "specialization_id": self.specialization_id,
            "name": self.name,
            "description": self.description
        }


class RoadNode(Base):
    __tablename__ = "road_nodes"

    node_id = Column(String(10), primary_key=True)  # e.g., 'A', 'B', 'C'
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    hospitals = relationship("Hospital", back_populates="node")
    ambulances = relationship("Ambulance", back_populates="node")

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude
        }


class RoadEdge(Base):
    __tablename__ = "road_edges"

    edge_id = Column(Integer, primary_key=True, autoincrement=True)
    source_node = Column(String(10), ForeignKey("road_nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    destination_node = Column(String(10), ForeignKey("road_nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    distance_km = Column(Float, nullable=False)
    traffic_level = Column(String(20), default="Low", nullable=False)  # Low, Medium, High
    traffic_multiplier = Column(Float, default=1.0, nullable=False)    # 1.0, 1.4, 2.0
    base_travel_time_minutes = Column(Float, nullable=False)
    travel_time_minutes = Column(Float, nullable=False)
    is_bidirectional = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="Open", nullable=False)        # Open, Closed, Congested

    __table_args__ = (
        CheckConstraint("distance_km > 0", name="chk_positive_distance"),
        CheckConstraint("travel_time_minutes > 0", name="chk_positive_travel_time"),
    )

    def to_dict(self):
        return {
            "edge_id": self.edge_id,
            "source_node": self.source_node,
            "destination_node": self.destination_node,
            "distance_km": self.distance_km,
            "traffic_level": self.traffic_level,
            "traffic_multiplier": self.traffic_multiplier,
            "base_travel_time_minutes": self.base_travel_time_minutes,
            "travel_time_minutes": self.travel_time_minutes,
            "is_bidirectional": self.is_bidirectional,
            "status": self.status
        }


class Hospital(Base):
    __tablename__ = "hospitals"

    hospital_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False, index=True)
    address = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    node_id = Column(String(10), ForeignKey("road_nodes.node_id"), nullable=False, index=True)
    beds_available = Column(Integer, default=0, nullable=False)
    total_beds = Column(Integer, default=20, nullable=False)
    contact_number = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("beds_available >= 0", name="chk_non_negative_beds"),
        CheckConstraint("beds_available <= total_beds", name="chk_beds_available_limit"),
    )

    node = relationship("RoadNode", back_populates="hospitals")
    specializations = relationship("Specialization", secondary=hospital_specializations, back_populates="hospitals")
    dispatch_results = relationship("DispatchResult", back_populates="hospital")

    def to_dict(self):
        return {
            "hospital_id": self.hospital_id,
            "name": self.name,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "node": self.node_id,
            "node_id": self.node_id,
            "beds_available": self.beds_available,
            "total_beds": self.total_beds,
            "contact_number": self.contact_number,
            "is_active": self.is_active,
            "specializations": [s.name for s in self.specializations],
            "specialization": self.specializations[0].name if self.specializations else "General",
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Ambulance(Base):
    __tablename__ = "ambulances"

    ambulance_id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_number = Column(String(30), unique=True, nullable=False, index=True)
    current_node = Column(String(10), ForeignKey("road_nodes.node_id"), nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(String(30), default="Available", nullable=False)  # Available, Dispatched, Maintenance, Unavailable
    driver_name = Column(String(80), nullable=True)
    contact_number = Column(String(30), nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    node = relationship("RoadNode", back_populates="ambulances")
    dispatch_results = relationship("DispatchResult", back_populates="ambulance")

    def to_dict(self):
        return {
            "ambulance_id": self.ambulance_id,
            "vehicle_number": self.vehicle_number,
            "current_node": self.current_node,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "status": self.status,
            "driver_name": self.driver_name,
            "contact_number": self.contact_number,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


class EmergencyRequest(Base):
    __tablename__ = "emergency_requests"

    request_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_location_node = Column(String(10), ForeignKey("road_nodes.node_id"), nullable=False, index=True)
    severity = Column(String(20), default="Medium", nullable=False)  # Low, Medium, High
    required_specialization = Column(String(80), default="General", nullable=False)
    caller_name = Column(String(80), nullable=True)
    caller_phone = Column(String(30), nullable=True)
    status = Column(String(30), default="Dispatched", nullable=False)  # Pending, Dispatched, Completed, Cancelled
    request_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    dispatch_result = relationship("DispatchResult", back_populates="request", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        result = {
            "request_id": self.request_id,
            "patient_location_node": self.patient_location_node,
            "severity": self.severity,
            "required_specialization": self.required_specialization,
            "caller_name": self.caller_name,
            "caller_phone": self.caller_phone,
            "status": self.status,
            "request_timestamp": self.request_timestamp.isoformat() if self.request_timestamp else None
        }
        if self.dispatch_result:
            result["dispatch"] = self.dispatch_result.to_dict()
        return result


class DispatchResult(Base):
    __tablename__ = "dispatch_results"

    dispatch_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("emergency_requests.request_id", ondelete="CASCADE"), unique=True, nullable=False)
    recommended_hospital_id = Column(Integer, ForeignKey("hospitals.hospital_id"), nullable=False)
    assigned_ambulance_id = Column(Integer, ForeignKey("ambulances.ambulance_id"), nullable=True)
    calculated_route = Column(Text, nullable=False)  # JSON-encoded array of node IDs
    total_distance_km = Column(Float, nullable=False)
    estimated_travel_time_minutes = Column(Float, nullable=False)
    suitability_score = Column(Float, nullable=False)
    selection_reasoning = Column(Text, nullable=True)
    alternative_candidates = Column(Text, nullable=True)  # JSON-encoded array of candidate objects
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    request = relationship("EmergencyRequest", back_populates="dispatch_result")
    hospital = relationship("Hospital", back_populates="dispatch_results")
    ambulance = relationship("Ambulance", back_populates="dispatch_results")

    def get_route_list(self):
        try:
            return json.loads(self.calculated_route)
        except Exception:
            return [self.calculated_route]

    def get_alternatives_list(self):
        try:
            return json.loads(self.alternative_candidates) if self.alternative_candidates else []
        except Exception:
            return []

    def to_dict(self):
        return {
            "dispatch_id": self.dispatch_id,
            "request_id": self.request_id,
            "recommended_hospital_id": self.recommended_hospital_id,
            "hospital_name": self.hospital.name if self.hospital else None,
            "hospital_node": self.hospital.node_id if self.hospital else None,
            "assigned_ambulance_id": self.assigned_ambulance_id,
            "ambulance_vehicle": self.ambulance.vehicle_number if self.ambulance else None,
            "route": self.get_route_list(),
            "total_distance_km": self.total_distance_km,
            "estimated_travel_time_minutes": self.estimated_travel_time_minutes,
            "suitability_score": self.suitability_score,
            "selection_reasoning": self.selection_reasoning,
            "alternative_candidates": self.get_alternatives_list(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
