"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_participants = {}
    for activity_name, activity_data in activities.items():
        original_participants[activity_name] = activity_data["participants"].copy()
    
    yield
    
    # Restore original state after test
    for activity_name, participants in original_participants.items():
        activities[activity_name]["participants"] = participants


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint"""
    
    def test_get_activities(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert isinstance(data, dict)
        assert "Basketball Team" in data
        assert "Soccer Club" in data
        assert "Art Club" in data
        
        # Verify activity structure
        basketball = data["Basketball Team"]
        assert "description" in basketball
        assert "schedule" in basketball
        assert "max_participants" in basketball
        assert "participants" in basketball
    
    def test_activities_have_required_fields(self, client):
        """Test that all activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in data.items():
            for field in required_fields:
                assert field in activity_data, f"{activity_name} missing {field}"


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        email = "test@mergington.edu"
        activity_name = "Art Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify student was added to participants
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        email = "test@mergington.edu"
        activity_name = "Nonexistent Activity"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_student(self, client):
        """Test that a student cannot sign up for the same activity twice"""
        email = "test@mergington.edu"
        activity_name = "Drama Club"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_multiple_students(self, client):
        """Test that multiple students can sign up for the same activity"""
        activity_name = "Debate Team"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all students were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        for email in emails:
            assert email in activities_data[activity_name]["participants"]


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""
    
    def test_unregister_from_activity_success(self, client):
        """Test successful unregistration from an activity"""
        email = "test@mergington.edu"
        activity_name = "Math Club"
        
        # First sign up
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistration from an activity that doesn't exist"""
        email = "test@mergington.edu"
        activity_name = "Nonexistent Activity"
        
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_student_not_registered(self, client):
        """Test unregistering a student who is not registered"""
        email = "notregistered@mergington.edu"
        activity_name = "Soccer Club"
        
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_preexisting_participant(self, client):
        """Test unregistering a student who was already in the system"""
        email = "emma@mergington.edu"
        activity_name = "Programming Class"
        
        # Verify student is already registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        assert response.status_code == 200
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]


class TestIntegration:
    """Integration tests for the complete workflow"""
    
    def test_complete_signup_unregister_workflow(self, client):
        """Test complete workflow of signing up and unregistering"""
        email = "workflow@mergington.edu"
        activity_name = "Basketball Team"
        
        # Check initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity_name]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities")
        after_signup_data = after_signup.json()
        assert len(after_signup_data[activity_name]["participants"]) == initial_count + 1
        assert email in after_signup_data[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        after_unregister = client.get("/activities")
        after_unregister_data = after_unregister.json()
        assert len(after_unregister_data[activity_name]["participants"]) == initial_count
        assert email not in after_unregister_data[activity_name]["participants"]
