# tests/test_scheduling_api.py
import pytest
import json
from App.models import User, Admin, Staff, Schedule
from App.database import db

class TestSchedulingAPI:

    def test_get_strategies(self, client, init_database):
        """Test getting available strategies via API"""
        response = client.get('/api/scheduling/strategies')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'strategies' in data
        # Verify all three strategies are available
        assert 'even_distribute' in data['strategies']
        assert 'minimize_days' in data['strategies']
        assert 'shift_type_optimize' in data['strategies']

    def test_auto_populate_schedule_success(self, client, init_database):
        """Test successful schedule auto-population via API"""
        # Create test users directly in database
        admin = Admin(username="api_admin", password="password")
        staff1 = Staff(username="api_staff1", password="password")
        staff2 = Staff(username="api_staff2", password="password")
        
        db.session.add_all([admin, staff1, staff2])
        db.session.commit()
        
        # Test the special feature API endpoint
        data = {
            "admin_id": admin.id,
            "strategy_name": "even_distribute",  # Testing strategy pattern via API
            "staff_ids": [staff1.id, staff2.id],
            "start_date": "2024-01-01",
            "end_date": "2024-01-03"
        }
        
        response = client.post(
            '/api/scheduling/auto-populate',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'schedule_id' in data
        assert 'strategy_used' in data  # Verify strategy pattern is working via API
        assert 'score' in data  # Verify scoring system works

    def test_auto_populate_different_strategies(self, client, init_database):
        """Test that different strategies work via API"""
        admin = Admin(username="multi_admin", password="password")
        staff1 = Staff(username="multi_staff1", password="password")
        staff2 = Staff(username="multi_staff2", password="password")
        
        db.session.add_all([admin, staff1, staff2])
        db.session.commit()
        
        # Test multiple strategies
        strategies = ['even_distribute', 'minimize_days', 'shift_type_optimize']
        
        for strategy in strategies:
            data = {
                "admin_id": admin.id,
                "strategy_name": strategy,
                "staff_ids": [staff1.id, staff2.id],
                "start_date": "2024-01-01", 
                "end_date": "2024-01-02"
            }
            
            response = client.post(
                '/api/scheduling/auto-populate',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            assert response.status_code == 201
            result_data = json.loads(response.data)
            assert result_data['success'] == True
            assert result_data['strategy_used'] == strategy

    def test_compare_strategies_api(self, client, init_database):
        """Test strategy comparison feature via API"""
        admin = Admin(username="compare_admin", password="password")
        staff1 = Staff(username="compare_staff1", password="password")
        staff2 = Staff(username="compare_staff2", password="password")
        
        db.session.add_all([admin, staff1, staff2])
        db.session.commit()
        
        data = {
            "admin_id": admin.id,
            "staff_ids": [staff1.id, staff2.id],
            "start_date": "2024-01-01",
            "end_date": "2024-01-02"
        }
        
        response = client.post(
            '/api/scheduling/compare',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'comparison' in data
        # Verify all strategies were compared via API
        assert 'even_distribute' in data['comparison']
        assert 'minimize_days' in data['comparison'] 
        assert 'shift_type_optimize' in data['comparison']
        assert 'best_strategy' in data

    def test_auto_populate_invalid_strategy_api(self, client, init_database):
        """Test error handling for invalid strategy via API"""
        admin = Admin(username="error_admin", password="password")
        staff = Staff(username="error_staff", password="password")
        
        db.session.add_all([admin, staff])
        db.session.commit()
        
        data = {
            "admin_id": admin.id,
            "strategy_name": "invalid_strategy",  
            "staff_ids": [staff.id],
            "start_date": "2024-01-01",
            "end_date": "2024-01-02"
        }
        
        response = client.post(
            '/api/scheduling/auto-populate',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'error' in data

    def test_auto_populate_no_staff_api(self, client, init_database):
        """Test auto-populate with no staff members via API"""
        admin = Admin(username="nostaff_admin", password="password")
        db.session.add(admin)
        db.session.commit()
        
        data = {
            "admin_id": admin.id,
            "strategy_name": "even_distribute",
            "staff_ids": [],  
            "start_date": "2024-01-01",
            "end_date": "2024-01-02"
        }
        
        response = client.post(
            '/api/scheduling/auto-populate',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False

    def test_get_schedules_api(self, client, init_database):
        """Test getting schedules via API"""
        response = client.get('/api/schedules')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'schedules' in data

    def test_get_schedule_details_api(self, client, init_database):
        """Test getting specific schedule details via API"""
        # First create a schedule
        admin = Admin(username="detail_admin", password="password")
        staff = Staff(username="detail_staff", password="password")
        
        db.session.add_all([admin, staff])
        db.session.commit()
        
        schedule = Schedule(name="Test Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()
        
        response = client.get(f'/api/schedules/{schedule.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'schedule' in data