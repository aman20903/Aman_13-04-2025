#uptime_calculator.py
import csv
import os
import pytz
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import StoreStatus, BusinessHours, StoreTimezone, Report
from typing import Dict, List, Tuple, Optional

def get_current_timestamp(db: Session) -> datetime:
    """Get the max timestamp from the store_status table as the "current" time"""
    max_timestamp = db.query(func.max(StoreStatus.timestamp_utc)).scalar()
    return max_timestamp or datetime.utcnow()

def get_store_timezone(store_id: str, db: Session) -> str:
    """Get the timezone for a store, default to America/Chicago if not found"""
    timezone_record = db.query(StoreTimezone).filter(StoreTimezone.store_id == store_id).first()
    return timezone_record.timezone_str if timezone_record else "America/Chicago"

def get_business_hours(store_id: str, db: Session) -> Dict[int, List[Tuple[time, time]]]:
    """
    Get business hours for a store by day of week
    Returns a dict mapping day of week (0=Monday, 6=Sunday) to a list of (start_time, end_time) tuples
    If no hours are found, assumes 24/7 operation
    """
    hours_records = db.query(BusinessHours).filter(BusinessHours.store_id == store_id).all()
    
    business_hours = {}
    for record in hours_records:
        day = record.day_of_week
        if day not in business_hours:
            business_hours[day] = []
        business_hours[day].append((record.start_time_local, record.end_time_local))
    
    # If no business hours, assume 24/7
    if not business_hours:
        # For each day of week, add 00:00 to 23:59:59
        for day in range(7):
            business_hours[day] = [(time(0, 0, 0), time(23, 59, 59))]
    
    return business_hours

def is_within_business_hours(timestamp_local: datetime, business_hours: Dict[int, List[Tuple[time, time]]]) -> bool:
    """Check if a local timestamp is within business hours"""
    day_of_week = timestamp_local.weekday()  # 0=Monday, 6=Sunday
    
    # Get business hours for this day
    day_hours = business_hours.get(day_of_week, [])
    
    # If no specific hours for this day, check if we have 24/7 setup
    if not day_hours and 0 in business_hours and business_hours[0][0] == (time(0, 0, 0), time(23, 59, 59)):
        return True
    
    # Check if timestamp is within any business hour interval for this day
    timestamp_time = timestamp_local.time()
    for start_time, end_time in day_hours:
        if start_time <= timestamp_time <= end_time:
            return True
    
    return False

def calculate_uptime_downtime(
    store_id: str,
    db: Session,
    current_time: datetime,
    timezone_str: str,
    business_hours: Dict[int, List[Tuple[time, time]]]
) -> Dict[str, float]:
    """
    Calculate uptime and downtime for a store for the last hour, day, and week
    Returns a dict with the calculated values
    """
    # Convert current_time to the store's timezone
    tz = pytz.timezone(timezone_str)
    current_time_local = current_time.replace(tzinfo=pytz.UTC).astimezone(tz)
    
    # Calculate time ranges for last hour, day, week in UTC
    one_hour_ago = current_time - timedelta(hours=1)
    one_day_ago = current_time - timedelta(days=1)
    one_week_ago = current_time - timedelta(weeks=1)
    
    # Get store status observations for the last week
    observations = db.query(StoreStatus)\
        .filter(StoreStatus.store_id == store_id)\
        .filter(StoreStatus.timestamp_utc >= one_week_ago)\
        .filter(StoreStatus.timestamp_utc <= current_time)\
        .order_by(StoreStatus.timestamp_utc)\
        .all()
    
    # Init results
    results = {
        "uptime_last_hour": 0.0,
        "uptime_last_day": 0.0,
        "uptime_last_week": 0.0,
        "downtime_last_hour": 0.0,
        "downtime_last_day": 0.0,
        "downtime_last_week": 0.0
    }
    
    if not observations:
        return results
    
    # Convert observations to local time and filter by business hours
    local_observations = []
    for obs in observations:
        local_time = obs.timestamp_utc.replace(tzinfo=pytz.UTC).astimezone(tz)
        if is_within_business_hours(local_time, business_hours):
            local_observations.append({
                "timestamp_utc": obs.timestamp_utc,
                "timestamp_local": local_time,
                "status": obs.status
            })
    
    if not local_observations:
        return results
    
    # Calculate time intervals between observations
    intervals = []
    for i in range(len(local_observations) - 1):
        current_obs = local_observations[i]
        next_obs = local_observations[i + 1]
        
        interval_length = (next_obs["timestamp_utc"] - current_obs["timestamp_utc"]).total_seconds() / 60  # in minutes
        status = current_obs["status"]
        
        # Create interval
        interval = {
            "start_time": current_obs["timestamp_utc"],
            "end_time": next_obs["timestamp_utc"],
            "status": status,
            "duration_minutes": interval_length
        }
        intervals.append(interval)
    
    # Calculate uptime and downtime for each time range
    for interval in intervals:
        is_active = interval["status"] == "active"
        
        # Check if interval is in the last hour
        if interval["end_time"] >= one_hour_ago:
            start_in_range = max(interval["start_time"], one_hour_ago)
            end_in_range = min(interval["end_time"], current_time)
            duration_in_range = (end_in_range - start_in_range).total_seconds() / 60  # in minutes
            
            if is_active:
                results["uptime_last_hour"] += duration_in_range
            else:
                results["downtime_last_hour"] += duration_in_range
        
        # Check if interval is in the last day
        if interval["end_time"] >= one_day_ago:
            start_in_range = max(interval["start_time"], one_day_ago)
            end_in_range = min(interval["end_time"], current_time)
            duration_in_range = (end_in_range - start_in_range).total_seconds() / 3600  # in hours
            
            if is_active:
                results["uptime_last_day"] += duration_in_range
            else:
                results["downtime_last_day"] += duration_in_range
        
        # Check if interval is in the last week
        if interval["end_time"] >= one_week_ago:
            start_in_range = max(interval["start_time"], one_week_ago)
            end_in_range = min(interval["end_time"], current_time)
            duration_in_range = (end_in_range - start_in_range).total_seconds() / 3600  # in hours
            
            if is_active:
                results["uptime_last_week"] += duration_in_range
            else:
                results["downtime_last_week"] += duration_in_range
    
    return results

def generate_report(db: Session, report_id: str) -> str:
    """
    Generate a report of store uptime/downtime
    Returns the path to the generated CSV file
    """
    current_time = get_current_timestamp(db)
    
    # Get all unique store IDs
    store_ids = db.query(StoreStatus.store_id).distinct().all()
    store_ids = [store_id[0] for store_id in store_ids]
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Create file path
    file_path = os.path.join(reports_dir, f"{report_id}.csv")
    
    # Generate report
    with open(file_path, 'w', newline='') as csvfile:
        fieldnames = [
            'store_id', 
            'uptime_last_hour(in minutes)', 
            'uptime_last_day(in hours)', 
            'uptime_last_week(in hours)', 
            'downtime_last_hour(in minutes)', 
            'downtime_last_day(in hours)', 
            'downtime_last_week(in hours)'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Process each store
        for store_id in store_ids:
            # Get store timezone
            timezone_str = get_store_timezone(store_id, db)
            
            # Get business hours
            business_hours = get_business_hours(store_id, db)
            
            # Calculate uptime/downtime
            results = calculate_uptime_downtime(store_id, db, current_time, timezone_str, business_hours)
            
            # Write row to CSV
            writer.writerow({
                'store_id': store_id,
                'uptime_last_hour(in minutes)': round(results["uptime_last_hour"], 2),
                'uptime_last_day(in hours)': round(results["uptime_last_day"], 2),
                'uptime_last_week(in hours)': round(results["uptime_last_week"], 2),
                'downtime_last_hour(in minutes)': round(results["downtime_last_hour"], 2),
                'downtime_last_day(in hours)': round(results["downtime_last_day"], 2),
                'downtime_last_week(in hours)': round(results["downtime_last_week"], 2)
            })
    
    return file_path