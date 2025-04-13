import csv
import zipfile
import os
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import StoreStatus, BusinessHours, StoreTimezone
import io
import pytz
from datetime import time

def extract_zip_file(zip_path, extract_to=None):
    """Extract the contents of the zip file, handling nested zip files if necessary"""
    if extract_to is None:
        # Extract to the same directory as the zip file
        extract_to = os.path.dirname(zip_path)
    
    # Create a specific extraction folder
    extract_dir = os.path.join(extract_to, "extracted_data")
    os.makedirs(extract_dir, exist_ok=True)
    
    print(f"Extracting {zip_path} to {extract_dir}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # List extracted contents
    extracted_files = os.listdir(extract_dir)
    print(f"Extracted files: {extracted_files}")
    
    # Look for CSV files directly or in subdirectories
    csv_files = {}
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        header = next(csv.reader(f))
                        if 'store_id' in header and 'timestamp_utc' in header and 'status' in header:
                            csv_files['status'] = file_path
                        elif 'store_id' in header and 'day' in header and 'start_time_local' in header:
                            csv_files['hours'] = file_path
                        elif 'store_id' in header and 'timezone_str' in header:
                            csv_files['timezone'] = file_path
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    print(f"Identified CSV files: {csv_files}")
    return csv_files

def load_store_status(file_path, db: Session):
    """Load store status data from CSV to database"""
    print(f"Loading store status from {file_path}")
    with open(file_path, 'r') as f:
        csv_reader = csv.DictReader(f)
        batch_size = 1000
        batch = []
        
        for row in csv_reader:
            # Convert timestamp string to datetime object
            timestamp_str = row['timestamp_utc']
            try:
                if '.' in timestamp_str and ' UTC' in timestamp_str:
                    # Format: 2023-01-01 12:30:45.123 UTC
                    timestamp_utc = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f %Z')
                elif ' UTC' in timestamp_str:
                    # Format: 2023-01-01 12:30:45 UTC
                    timestamp_utc = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S %Z')
                else:
                    # Try a generic format
                    timestamp_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                # If all else fails, try a basic format
                try:
                    timestamp_utc = datetime.strptime(timestamp_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"Could not parse timestamp: {timestamp_str}, skipping row")
                    continue
            
            store_status = StoreStatus(
                store_id=row['store_id'],
                timestamp_utc=timestamp_utc,
                status=row['status']
            )
            batch.append(store_status)
            
            # Commit in batches for better performance
            if len(batch) >= batch_size:
                db.add_all(batch)
                db.commit()
                batch = []
        
        # Add any remaining records
        if batch:
            db.add_all(batch)
            db.commit()
        
        print(f"Finished loading store status data")

def load_business_hours(file_path, db: Session):
    """Load business hours data from CSV to database"""
    print(f"Loading business hours from {file_path}")
    with open(file_path, 'r') as f:
        csv_reader = csv.DictReader(f)
        batch_size = 1000
        batch = []
        
        for row in csv_reader:
            # Convert time strings to time objects
            try:
                start_time_local = datetime.strptime(row['start_time_local'], '%H:%M:%S').time()
                end_time_local = datetime.strptime(row['end_time_local'], '%H:%M:%S').time()
                
                business_hour = BusinessHours(
                    store_id=row['store_id'],
                    day_of_week=int(row['day']),
                    start_time_local=start_time_local,
                    end_time_local=end_time_local
                )
                batch.append(business_hour)
                
                # Commit in batches for better performance
                if len(batch) >= batch_size:
                    db.add_all(batch)
                    db.commit()
                    batch = []
            except Exception as e:
                print(f"Error loading business hour: {e} for row {row}")
        
        # Add any remaining records
        if batch:
            db.add_all(batch)
            db.commit()
        
        print(f"Finished loading business hours data")

def load_store_timezone(file_path, db: Session):
    """Load store timezone data from CSV to database"""
    print(f"Loading store timezone from {file_path}")
    with open(file_path, 'r') as f:
        csv_reader = csv.DictReader(f)
        batch_size = 1000
        batch = []
        
        for row in csv_reader:
            # Handle missing or invalid timezone data
            timezone_str = row.get('timezone_str', 'America/Chicago')
            if not timezone_str or timezone_str.strip() == '':
                timezone_str = 'America/Chicago'
            
            # Validate timezone
            try:
                pytz.timezone(timezone_str)
            except pytz.exceptions.UnknownTimeZoneError:
                timezone_str = 'America/Chicago'
            
            store_timezone = StoreTimezone(
                store_id=row['store_id'],
                timezone_str=timezone_str
            )
            batch.append(store_timezone)
            
            # Commit in batches for better performance
            if len(batch) >= batch_size:
                db.add_all(batch)
                db.commit()
                batch = []
        
        # Add any remaining records
        if batch:
            db.add_all(batch)
            db.commit()
        
        print(f"Finished loading store timezone data")

def load_all_data(db: Session, zip_path=None):
    """Load all data from CSV files to database"""
    try:
        if zip_path and os.path.exists(zip_path):
            print(f"Processing zip file: {zip_path}")
            csv_files = extract_zip_file(zip_path)
            
            # Load data if files were found
            if 'timezone' in csv_files:
                load_store_timezone(csv_files['timezone'], db)
            else:
                print("Timezone CSV file not found!")
            
            if 'hours' in csv_files:
                load_business_hours(csv_files['hours'], db)
            else:
                print("Business hours CSV file not found!")
            
            if 'status' in csv_files:
                load_store_status(csv_files['status'], db)
            else:
                print("Store status CSV file not found!")
        else:
            # paths for standalone CSV files
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            os.makedirs(data_dir, exist_ok=True)
            print(f"Looking for CSV files in {data_dir}")
            
            status_file = os.path.join(data_dir, 'store_status.csv')
            hours_file = os.path.join(data_dir, 'business_hours.csv')
            timezone_file = os.path.join(data_dir, 'timezone.csv')
            
            # Check if files exist
            files_exist = all(os.path.exists(f) for f in [status_file, hours_file, timezone_file])
            if files_exist:
                load_store_timezone(timezone_file, db)
                load_business_hours(hours_file, db)
                load_store_status(status_file, db)
            else:
                print("CSV files not found in data directory and no zip file provided.")
                print(f"Missing files: {[f for f in [status_file, hours_file, timezone_file] if not os.path.exists(f)]}")
        
        print("Data loading complete!")
    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise