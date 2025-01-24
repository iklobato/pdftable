from fastapi import FastAPI, UploadFile, Request, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from tabula.io import read_pdf
import pandas as pd
import os
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

app = FastAPI(title="PDF Table Extractor")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

def convert_table_to_dict(table: pd.DataFrame, table_id: str) -> Dict:
    """Convert a pandas DataFrame to a dictionary with HTML and metadata."""
    return {
        'id': table_id,
        'html': table.to_html(
            classes=['table', 'table-striped', 'table-bordered', 'table-hover', 'editable-table'],
            index=False
        ),
        'data': table.to_dict(orient='records'),
        'columns': table.columns.tolist(),
        'rows': len(table),
        'num_columns': len(table.columns)
    }

@app.post("/extract-tables")
async def extract_tables(file: UploadFile):
    # Save the uploaded file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = UPLOAD_DIR / f"{timestamp}_{file.filename}"
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    try:
        # Extract tables from PDF using tabula-io
        tables = read_pdf(
            str(file_path),
            pages='all',
            multiple_tables=True,
            guess=True,
            pandas_options={'header': 'infer'}
        )
        
        # Convert tables to HTML format with data
        tables_data = []
        for i, table in enumerate(tables):
            # Clean the table data
            table = table.fillna('')  # Replace NaN with empty string
            table_data = convert_table_to_dict(table, f'table-{i+1}')
            tables_data.append(table_data)
        
        return {
            "status": "success",
            "tables": tables_data,
            "message": f"Successfully extracted {len(tables)} tables",
            "file_id": timestamp
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error processing PDF: {str(e)}"
        }
    finally:
        # Clean up the uploaded file after 1 hour (you might want to implement this with a background task)
        os.remove(file_path)

@app.post("/update-table")
async def update_table(
    table_data: Dict = Body(...),
):
    try:
        # Convert the received data back to a pandas DataFrame
        table = pd.DataFrame(table_data['data'])
        
        # Generate updated table information
        updated_table = convert_table_to_dict(table, table_data['id'])
        
        # Generate CSV data for download
        csv_data = table.to_csv(index=False)
        
        return {
            "status": "success",
            "table": updated_table,
            "csv_data": csv_data,
            "message": "Table updated successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error updating table: {str(e)}"
        }

@app.post("/download-table")
async def download_table(table_data: Dict = Body(...)):
    try:
        # Convert the received data to a DataFrame
        table = pd.DataFrame(table_data['data'])
        
        # Convert to various formats
        formats = {
            'csv': table.to_csv(index=False),
            'excel': table.to_excel(index=False),
            'json': table.to_json(orient='records')
        }
        
        return {
            "status": "success",
            "formats": formats,
            "message": "Table data prepared for download"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error preparing table for download: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

