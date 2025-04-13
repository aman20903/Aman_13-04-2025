from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import os
from .db import engine, get_db, Base
from .api.routes import router as api_router
from .utils.csv_loader import load_all_data

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Store Monitoring API")

# Include API routes
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Load data from CSVs on startup if needed"""
    db = next(get_db())
    try:
        # Check if data is already loaded
        from .models import StoreStatus
        count = db.query(StoreStatus).count()
        print(f"Found {count} existing store status records")
        
        if count == 0:
            # Load data from zip file
            zip_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'store-monitoring-data.zip')
            if os.path.exists(zip_path):
                print(f"Loading data from {zip_path}...")
                load_all_data(db, zip_path)
            else:
                print(f"ZIP file not found at {zip_path}. Looking for CSV files...")
                load_all_data(db)
        else:
            print("Data already loaded, skipping import")
    except Exception as e:
        print(f"Error during startup: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to Store Monitoring API"}