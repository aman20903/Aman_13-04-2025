#schema.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ReportResponse(BaseModel):
    report_id: str

class ReportStatusResponse(BaseModel):
    status: str
    file_url: Optional[str] = None

class StoreUptimeReport(BaseModel):
    store_id: str
    # Original time measurements
    uptime_last_hour: float  # in minutes
    uptime_last_day: float  # in hours
    uptime_last_week: float  # in hours
    downtime_last_hour: float  # in minutes
    downtime_last_day: float  # in hours
    downtime_last_week: float  # in hours
    
    # Added percentage measurements
    uptime_last_hour_pct: float  # percentage
    uptime_last_day_pct: float  # percentage
    uptime_last_week_pct: float  # percentage
    downtime_last_hour_pct: float  # percentage
    downtime_last_day_pct: float  # percentage
    downtime_last_week_pct: float  # percentage

    class Config:
        orm_mode = True