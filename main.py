import tempfile
import logging
from fastapi import FastAPI, UploadFile, Request, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from tabula.io import read_pdf
import pandas as pd
import os
import base64
from io import BytesIO
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

app = FastAPI(title="PDF Table Extractor")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/_ah/warmup")
async def warmup():
    return {"status": "warmed"}

@app.get("/health")
@app.get("/healthz")
async def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    logging.info(f"Serving home page to {request.client}")
    return templates.TemplateResponse("index.html", {"request": request})

def convert_table_to_dict(table: pd.DataFrame, table_id: str) -> Dict:
    return {
        'id': table_id,
        'html': table.to_html(
            classes=[
                'table',
                'table-striped',
                'table-bordered',
                'table-hover',
                'editable-table',
            ],
            index=False,
        ),
        'data': table.to_dict(orient='records'),
        'columns': table.columns.tolist(),
        'rows': len(table),
        'num_columns': len(table.columns),
    }

@app.post("/extract-tables")
async def extract_tables(file: UploadFile):
   with tempfile.NamedTemporaryFile(delete=False) as tmp:
       content = await file.read()
       tmp.write(content)
       tmp_path = tmp.name

   try:
       tables = read_pdf(
           tmp_path,
           pages='all',
           multiple_tables=True,
           guess=True,
           pandas_options={'header': 'infer'},
       )

       tables_data = []
       for i, table in enumerate(tables):
           table = table.fillna('')
           table_data = convert_table_to_dict(table, f'table-{i+1}')
           tables_data.append(table_data)

       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       return {
           "status": "success", 
           "tables": tables_data,
           "message": f"Successfully extracted {len(tables)} tables",
           "file_id": timestamp,
       }
   except Exception as e:
       logging.error(f"Error processing PDF: {str(e)}")
       return {"status": "error", "message": "Error processing PDF"}
   finally:
        logging.info(f"Deleting temporary file: {tmp_path}")
        os.unlink(tmp_path)

@app.post("/update-table")
async def update_table(
    table_data: Dict = Body(...),
):
    try:
        table = pd.DataFrame(table_data['data'])

        updated_table = convert_table_to_dict(table, table_data['id'])

        csv_data = table.to_csv(index=False)

        return {
            "status": "success",
            "table": updated_table,
            "csv_data": csv_data,
            "message": "Table updated successfully",
        }
    except Exception as e:
        return {"status": "error", "message": "Error updating table"}


@app.post("/download-table")
async def download_table(table_data: Dict = Body(...)):
    logging.info(f"Preparing table for download: {table_data['id']}")
    try:
        table = pd.DataFrame(table_data['data'])

        formats = {
            'csv': table.to_csv(index=False),
            'excel': table.to_excel(index=False),
            'json': table.to_json(orient='records'),
        }

        return {
            "status": "success",
            "formats": formats,
            "message": "Table data prepared for download",
        }
    except Exception as e:
        logging.error(f"Error preparing table for download: {str(e)}")
        return {
            "status": "error",
            "message": "Error preparing table for download",
        }


@app.post("/merge-tables")
async def merge_tables(tables_data: List[Dict] = Body(...)):
    logging.info(f"Merging {len(tables_data)} tables")
    logging.info(f"Received data: {tables_data}")
    try:
        if not tables_data:
            return {"status": "error", "message": "No table data received"}
            
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for i, table_data in enumerate(tables_data):
                df = pd.DataFrame(table_data['data'])
                logging.info(f"Processing table {i+1}, shape: {df.shape}")
                
                sheet_name = f"Table {i+1}"
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        excel_data = base64.b64encode(output.getvalue()).decode()
        logging.info(f"Excel file size: {len(excel_data)} bytes")
        
        return {
            "status": "success",
            "excel_data": excel_data,
            "message": f"Successfully merged {len(tables_data)} tables"
        }
    except Exception as e:
        logging.error(f"Error merging tables: {str(e)}")
        return {"status": "error", "message": "Error merging tables"}


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

