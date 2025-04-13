from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Time
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class StoreStatus(Base):
    __tablename__ = "store_status"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, index=True)
    timestamp_utc = Column(DateTime, index=True)
    status = Column(String)  # 'active' or 'inactive'

class BusinessHours(Base):
    __tablename__ = "business_hours"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, index=True)
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    start_time_local = Column(Time)
    end_time_local = Column(Time)

class StoreTimezone(Base):
    __tablename__ = "store_timezone"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, unique=True, index=True)
    timezone_str = Column(String)

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, unique=True, index=True)
    status = Column(String)  # 'running' or 'complete'
    created_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)
    file_path = Column(String, nullable=True)