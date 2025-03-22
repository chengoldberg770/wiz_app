from fastapi import FastAPI, HTTPException, Header, Depends, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
import sqlite3
import time
import datetime
import os
from contextlib import contextmanager

# Initialize the FastAPI app
app= FastAPI(title="Status API", description="A simple API for status updates")

# Start time for calculating uptime
START_TIME = time.time()

# Database setup
DB_PATH = "logs.db"

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT
        )
        ''')
        
        # Check if state table exists, if not create it
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            counter INTEGER DEFAULT 0,
            message TEXT DEFAULT 'Initial state'
        )
        ''')
        
        # Initialize state if not exists
        cursor.execute('SELECT * FROM state WHERE id = 1')
        if not cursor.fetchone():
            cursor.execute('INSERT INTO state (id, counter, message) VALUES (1, 0, "Initial state")')
        
        conn.commit()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Initialize database on startup
init_db()

#API Key authentication
API_KEY= "your-secret-api-key"

def verify_api_key(api_key: str= Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code= 401, detail= "Invalid API Key")
    return api_key

# Models for request and response
class UpdateRequest(BaseModel):
    counter: Optional[int] = None
    message: Optional[str] = None
    
    @validator('counter')
    def counter_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('counter must be non-negative')
        return v
    
    @validator('message')
    def message_must_not_be_empty(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError('message must not be empty')
        return v

class LogEntry(BaseModel):
    timestamp: str
    old_value: Dict[str, Any]
    new_value: Dict[str, Any]

class StatusResponse(BaseModel):
    counter: int
    message: str
    timestamp: str
    uptime: float  # in seconds

class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int
    page: int
    limit: int

# Helper function to get current state
def get_current_state():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT counter, message FROM state WHERE id = 1')
        result = cursor.fetchone()
        if result:
            return {"counter": result["counter"], "message": result["message"]}
        return {"counter": 0, "message": "Initial state"}

# Endpoints
@app.get("/status", response_model=StatusResponse)
async def get_status():
    current_state = get_current_state()
    return {
        **current_state,
        "timestamp": datetime.datetime.now().isoformat(),
        "uptime": time.time() - START_TIME
    }

@app.post("/update", response_model=Dict[str, Any])
async def update_state(update: UpdateRequest, api_key: str = Depends(verify_api_key)):
    old_state = get_current_state()
    new_state = old_state.copy()
    
    # Update state based on request
    if update.counter is not None:
        new_state["counter"] = update.counter
    if update.message is not None:
        new_state["message"] = update.message
    
    # Only proceed if there's an actual change
    if new_state != old_state:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Update state
            cursor.execute(
                'UPDATE state SET counter = ?, message = ? WHERE id = 1',
                (new_state["counter"], new_state["message"])
            )
            
            # Log the change
            cursor.execute(
                'INSERT INTO logs (timestamp, old_value, new_value) VALUES (?, ?, ?)',
                (
                    datetime.datetime.now().isoformat(),
                    str(old_state),
                    str(new_state)
                )
            )
            
            conn.commit()
    
    return {
        "old_state": old_state,
        "new_state": new_state,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/logs", response_model=LogsResponse)
async def get_logs(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute('SELECT COUNT(*) as count FROM logs')
        total = cursor.fetchone()["count"]
        
        # Get paginated logs
        offset = (page - 1) * limit
        cursor.execute('SELECT * FROM logs ORDER BY timestamp DESC LIMIT ? OFFSET ?', 
                      (limit, offset))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                "timestamp": row["timestamp"],
                "old_value": eval(row["old_value"]),  # Convert string to dict
                "new_value": eval(row["new_value"])   # Convert string to dict
            })
        
        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit
        }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)