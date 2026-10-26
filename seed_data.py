"""
Database seeding script for MedRoute Emergency Dispatch System.
Creates a realistic, internally consistent synthetic dataset including road nodes,
weighted edges, traffic levels, hospitals with multiple specializations,
ambulances, and historical emergency dispatch records.
"""

import sys
from datetime import datetime, timedelta
from database import init_db, get_session
from models import (
    RoadNode, RoadEdge, Specialization, Hospital, Ambulance,
    EmergencyRequest, DispatchResult
)
from config import Config


def seed_database(db=None):
    """Seed SQLite database with complete synthetic demonstration dataset."""
    close_at_end = False
    if db is None:
        init_db()
        db = get_session()
        close_at_end = True

    try:
        # Check if already seeded
        if db.query(RoadNode).count() > 0:
            print("Database already contains data. Clearing and re-seeding...")
            db.query(DispatchResult).delete()
            db.query(EmergencyRequest).delete()
            db.query(Ambulance).delete()
            db.query(Hospital).delete()
            db.query(RoadEdge).delete()
            db.query(RoadNode).delete()
            db.query(Specialization).delete()
            db.commit()

        print("Seeding specializations...")
        specializations = [
            Specialization(name="Cardiology", description="Cardiac emergencies, heart attacks, arrhythmia"),
            Specialization(name="Trauma", description="Critical accidents, multi-system trauma, acute hemorrhage"),
            Specialization(name="Orthopaedics", description="Fractures, joint dislocations, severe skeletal injuries"),
            Specialization(name="Neurology", description="Strokes, brain trauma, neurological acute conditions"),
            Specialization(name="Pediatrics", description="Emergency pediatric and neonatal intensive care"),
            Specialization(name="General", description="General medical acute care and stabilization")
        ]
        db.add_all(specializations)
        db.commit()

        spec_map = {s.name: s for s in db.query(Specialization).all()}

        print("Seeding road network nodes...")
        nodes = [
            RoadNode(node_id="A", name="Downtown Center", latitude=18.5204, longitude=73.8567),
            RoadNode(node_id="B", name="North Medical Hub", latitude=18.5600, longitude=73.8700),
            RoadNode(node_id="C", name="East Junction", latitude=18.5150, longitude=73.9260),
            RoadNode(node_id="D", name="South Healthcare District", latitude=18.4700, longitude=73.8600),
            RoadNode(node_id="E", name="West Suburb Interchange", latitude=18.5100, longitude=73.8050),
            RoadNode(node_id="F", name="Central Expressway Crossing", latitude=18.5350, longitude=73.8400),
            RoadNode(node_id="G", name="Tech Corridor Sector", latitude=18.5900, longitude=73.7800),
            RoadNode(node_id="H", name="Airport Highway Junction", latitude=18.5800, longitude=73.9200)
        ]
        db.add_all(nodes)
        db.commit()

        print("Seeding road network edges with distance and traffic...")
        # (source, dest, distance_km, traffic_level, traffic_multiplier, base_minutes)
        edges_data = [
            ("A", "B", 6.5, "Medium", 1.4, 9.0),
            ("A", "C", 4.2, "Low",    1.0, 6.0),
            ("A", "E", 5.0, "High",   2.0, 7.5),
            ("A", "F", 2.8, "Low",    1.0, 4.0),
            ("B", "D", 9.5, "Medium", 1.4, 13.0),
            ("B", "F", 4.0, "Low",    1.0, 5.5),
            ("B", "H", 7.0, "Low",    1.0, 9.0),
            ("C", "D", 7.8, "Medium", 1.4, 11.0),
            ("C", "H", 8.2, "Low",    1.0, 11.5),
            ("D", "E", 6.8, "Low",    1.0, 9.5),
            ("D", "F", 7.2, "Medium", 1.4, 10.0),
            ("E", "F", 3.5, "Low",    1.0, 5.0),
            ("E", "G", 8.0, "Medium", 1.4, 11.0),
            ("F", "G", 7.5, "High",   2.0, 10.5),
            ("G", "H", 12.0,"Low",    1.0, 16.0)
        ]

        edges = []
        for u, v, dist, traf, mult, base_m in edges_data:
            travel_time = round(base_m * mult, 1)
            edges.append(RoadEdge(
                source_node=u,
                destination_node=v,
                distance_km=dist,
                traffic_level=traf,
                traffic_multiplier=mult,
                base_travel_time_minutes=base_m,
                travel_time_minutes=travel_time,
                is_bidirectional=True,
                status="Open"
            ))
        db.add_all(edges)
        db.commit()

        print("Seeding hospitals and bed capacities...")
        h1 = Hospital(
            name="City Heart & Multi-Specialty Institute",
            address="104 South Medical Blvd",
            latitude=18.4710,
            longitude=73.8615,
            node_id="D",
            beds_available=8,
            total_beds=30,
            contact_number="+91-20-24451000",
            is_active=True
        )
        h1.specializations = [spec_map["Cardiology"], spec_map["Trauma"]]

        h2 = Hospital(
            name="Sunrise Emergency Hospital",
            address="22 North Road",
            latitude=18.5610,
            longitude=73.8710,
            node_id="B",
            beds_available=0,  # Zero beds: test exclusion
            total_beds=20,
            contact_number="+91-20-25532000",
            is_active=True
        )
        h2.specializations = [spec_map["Cardiology"], spec_map["General"]]

        h3 = Hospital(
            name="Metro Trauma & Orthopaedic Center",
            address="45 North Medical Hub",
            latitude=18.5580,
            longitude=73.8680,
            node_id="B",
            beds_available=7,
            total_beds=25,
            contact_number="+91-20-25593000",
            is_active=True
        )
        h3.specializations = [spec_map["Orthopaedics"], spec_map["Trauma"]]

        h4 = Hospital(
            name="Apollo General & Child Hospital",
            address="78 East Junction Ring",
            latitude=18.5140,
            longitude=73.9240,
            node_id="C",
            beds_available=14,
            total_beds=50,
            contact_number="+91-20-26614000",
            is_active=True
        )
        h4.specializations = [spec_map["General"], spec_map["Pediatrics"]]

        h5 = Hospital(
            name="Green Valley Neurology Institute",
            address="12 West Suburb Link",
            latitude=18.5090,
            longitude=73.8040,
            node_id="E",
            beds_available=5,
            total_beds=22,
            contact_number="+91-20-27715000",
            is_active=True
        )
        h5.specializations = [spec_map["Neurology"], spec_map["General"]]

        h6 = Hospital(
            name="Apex Critical Care Hospital",
            address="5 Expressway Interchange Square",
            latitude=18.5340,
            longitude=73.8390,
            node_id="F",
            beds_available=10,
            total_beds=40,
            contact_number="+91-20-28816000",
            is_active=True
        )
        h6.specializations = [spec_map["Cardiology"], spec_map["Trauma"], spec_map["General"]]

        h7 = Hospital(
            name="Highland Pediatric Specialty Center",
            address="9 Airport Highway",
            latitude=18.5810,
            longitude=73.9190,
            node_id="H",
            beds_available=6,
            total_beds=25,
            contact_number="+91-20-29917000",
            is_active=True
        )
        h7.specializations = [spec_map["Pediatrics"], spec_map["General"]]

        h8 = Hospital(
            name="West Outpost Clinic",
            address="99 Remote Tech Road",
            latitude=18.5910,
            longitude=73.7820,
            node_id="G",
            beds_available=3,
            total_beds=10,
            contact_number="+91-20-21118000",
            is_active=False  # Inactive: tests inactive exclusion
        )
        h8.specializations = [spec_map["General"]]

        db.add_all([h1, h2, h3, h4, h5, h6, h7, h8])
        db.commit()

        print("Seeding ambulance fleet...")
        ambulances = [
            Ambulance(vehicle_number="MH-12-AM-101", current_node="A", status="Available", driver_name="Ramesh Kumar", contact_number="+91-9822011001"),
            Ambulance(vehicle_number="MH-12-AM-102", current_node="B", status="Available", driver_name="Suresh Patil", contact_number="+91-9822011002"),
            Ambulance(vehicle_number="MH-12-AM-103", current_node="C", status="Dispatched", driver_name="Vikram Singh", contact_number="+91-9822011003"),
            Ambulance(vehicle_number="MH-12-AM-104", current_node="E", status="Available", driver_name="Aniket Shinde", contact_number="+91-9822011004"),
            Ambulance(vehicle_number="MH-12-AM-105", current_node="F", status="Maintenance", driver_name="Amit Deshmukh", contact_number="+91-9822011005")
        ]
        db.add_all(ambulances)
        db.commit()

        print("Seeding sample historical dispatches...")
        now = datetime.utcnow()
        req1 = EmergencyRequest(
            patient_location_node="A",
            severity="High",
            required_specialization="Cardiology",
            caller_name="Dr. Sharma",
            caller_phone="+91-9822123456",
            status="Completed",
            request_timestamp=now - timedelta(hours=3, minutes=15)
        )
        db.add(req1)
        db.commit()

        disp1 = DispatchResult(
            request_id=req1.request_id,
            recommended_hospital_id=h6.hospital_id,
            assigned_ambulance_id=ambulances[0].ambulance_id,
            calculated_route='["A", "F"]',
            total_distance_km=2.8,
            estimated_travel_time_minutes=4.0,
            suitability_score=94.5,
            selection_reasoning="Recommended as closest high-capacity cardiac center with 10 open beds and 4.0 min travel time.",
            alternative_candidates='[{"name": "City Heart & Multi-Specialty Institute", "distance_km": 10.0, "travel_time_minutes": 14.0, "beds_available": 8, "suitability_score": 78.2}]',
            created_at=now - timedelta(hours=3, minutes=14)
        )
        db.add(disp1)

        req2 = EmergencyRequest(
            patient_location_node="C",
            severity="Medium",
            required_specialization="Orthopaedics",
            caller_name="Pooja Verma",
            caller_phone="+91-9822654321",
            status="Dispatched",
            request_timestamp=now - timedelta(minutes=45)
        )
        db.add(req2)
        db.commit()

        disp2 = DispatchResult(
            request_id=req2.request_id,
            recommended_hospital_id=h3.hospital_id,
            assigned_ambulance_id=ambulances[2].ambulance_id,
            calculated_route='["C", "A", "F", "B"]',
            total_distance_km=11.0,
            estimated_travel_time_minutes=15.5,
            suitability_score=88.0,
            selection_reasoning="Best orthopedic facility available with 7 open beds.",
            alternative_candidates='[]',
            created_at=now - timedelta(minutes=44)
        )
        db.add(disp2)
        db.commit()

        print("Synthetic dataset successfully initialized and verified!")

    finally:
        if close_at_end:
            db.close()


if __name__ == "__main__":
    seed_database()
