**INSTALLATION**
Use command 
<ins>pip install -r requirements.txt</ins>
This will install dependencies which are required to run this app

Keep the zip folder in root directory

**Directory supposed to look like this**
store_monitoring/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── db.py
│   ├── utils/
│   │   ├── timezone_utils.py
│   │   ├── uptime_calculator.py
│   │   └── csv_loader.py
│   ├── api/
│   │   └── routes.py
├── reports/
│   └── <report_id>.csv
├── store-monitoring-data.zip
├── requirements.txt


**IMPORVEMENTS THAT CAN BE MADE FOR THE PROJECT**
1. Implement database indexing on frequently queried columns
2. Create separate service layers for business logic
3. Implement authentication and authorization for API endpoints
4. Create dashboards for visualizing store uptime data
5. Set up alerts for critical errors or unexpected downtime patterns
6. Create a dashboard UI for store owners to visualize their data
7. Add support for exporting reports in multiple formats (JSON, Excel, PDF)
