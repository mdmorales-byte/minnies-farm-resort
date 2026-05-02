"""
Supabase REST API Client for database operations
Uses HTTP requests instead of direct PostgreSQL connection
"""
import os
import urllib.request
import json
from functools import wraps

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Global cache for headers
_headers_cache = None

def get_headers():
    """Get Supabase API headers"""
    global _headers_cache
    if _headers_cache is None:
        _headers_cache = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    return _headers_cache

def supabase_request(endpoint, method='GET', data=None, params=None):
    """Make a request to Supabase REST API"""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    
    if params:
        query = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query}"
    
    headers = get_headers()
    req_data = json.dumps(data).encode('utf-8') if data else None
    
    req = urllib.request.Request(
        url,
        data=req_data,
        headers=headers,
        method=method
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 204:
                return None
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 409:  # Conflict (e.g., duplicate)
            return None
        raise

# User operations
def get_users():
    return supabase_request('users?select=*')

def get_user_by_email(email):
    result = supabase_request(f'users?email=eq.{email}&select=*')
    return result[0] if result else None

def get_user_by_id(user_id):
    result = supabase_request(f'users?id=eq.{user_id}&select=*')
    return result[0] if result else None

def create_user(user_data):
    return supabase_request('users', method='POST', data=user_data)

def update_user(user_id, user_data):
    return supabase_request(f'users?id=eq.{user_id}', method='PATCH', data=user_data)

# Room operations
def get_rooms():
    return supabase_request('rooms?select=*')

def get_room_by_id(room_id):
    result = supabase_request(f'rooms?id=eq.{room_id}&select=*')
    return result[0] if result else None

def create_room(room_data):
    return supabase_request('rooms', method='POST', data=room_data)

def update_room(room_id, room_data):
    return supabase_request(f'rooms?id=eq.{room_id}', method='PATCH', data=room_data)

def delete_room(room_id):
    return supabase_request(f'rooms?id=eq.{room_id}', method='DELETE')

# Service operations
def get_services():
    return supabase_request('services?select=*')

def get_service_by_id(service_id):
    result = supabase_request(f'services?id=eq.{service_id}&select=*')
    return result[0] if result else None

def create_service(service_data):
    return supabase_request('services', method='POST', data=service_data)

def update_service(service_id, service_data):
    return supabase_request(f'services?id=eq.{service_id}', method='PATCH', data=service_data)

def delete_service(service_id):
    return supabase_request(f'services?id=eq.{service_id}', method='DELETE')

# Booking operations
def get_bookings():
    return supabase_request('bookings?select=*')

def get_bookings_by_user(user_id):
    return supabase_request(f'bookings?user_id=eq.{user_id}&select=*')

def create_booking(booking_data):
    return supabase_request('bookings', method='POST', data=booking_data)

def update_booking(booking_id, booking_data):
    return supabase_request(f'bookings?id=eq.{booking_id}', method='PATCH', data=booking_data)

# Service avail operations
def get_service_avails():
    return supabase_request('service_avails?select=*')

def create_service_avail(avail_data):
    return supabase_request('service_avails', method='POST', data=avail_data)

# Review operations
def get_reviews():
    return supabase_request('reviews?select=*')

def create_review(review_data):
    return supabase_request('reviews', method='POST', data=review_data)
