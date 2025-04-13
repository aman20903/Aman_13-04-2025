from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Report
from ..schema import ReportResponse, ReportStatusResponse
from datetime import datetime
import uuid
import os
from ..utils.uptime_calculator import generate_report
from fastapi.responses import FileResponse

router = APIRouter()

@router.post("/trigger_report", response_model=ReportResponse)
def trigger_report(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Trigger the generation of a store uptime/downtime report
    Returns a report_id that can be used to poll for the report status
    """
    report_id = str(uuid.uuid4())
    
    # Create a new report record
    new_report = Report(
        report_id=report_id,
        status="running",
        created_at=datetime.utcnow()
    )
    db.add(new_report)
    db.commit()
    
    # Trigger report generation in the background
    background_tasks.add_task(process_report, report_id, db)
    
    return {"report_id": report_id}

@router.get("/get_report/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    """
    Get the status of a report or the CSV file if complete
    """
    report = db.query(Report).filter(Report.report_id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status == "running":
        return {"status": "Running"}
    
    if report.status == "failed":
        raise HTTPException(status_code=500, detail="Report generation failed")
    
    # If report is complete, return the CSV file
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=500, detail="Report file not found")
    
    return FileResponse(
        path=report.file_path,
        media_type="text/csv",
        filename=f"store_uptime_report_{report_id}.csv"
    )

def process_report(report_id: str, db: Session):
    """
    Background task to generate the report
    """
    try:
        # Get a new session since we're in a background task
        from ..db import SessionLocal
        db = SessionLocal()
        
        # Get the report from DB
        report = db.query(Report).filter(Report.report_id == report_id).first()
        
        if not report:
            print(f"Report {report_id} not found")
            return
        
        # Generate the report
        file_path = generate_report(db, report_id)
        
        # Update the report status
        report.status = "complete"
        report.completed_at = datetime.utcnow()
        report.file_path = file_path
        db.commit()
        
        print(f"Report {report_id} generated successfully at {file_path}")
    except Exception as e:
        print(f"Error generating report {report_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # If there's an error, update the report status
        try:
            report = db.query(Report).filter(Report.report_id == report_id).first()
            if report:
                report.status = "failed"
                db.commit()
        except Exception as inner_e:
            print(f"Error updating report status: {inner_e}")
    finally:
        db.close()