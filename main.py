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

app = FastAPI(title="PDF Table Extractor")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def convert_table_to_dict(table: pd.DataFrame, table_id: str) -> Dict:
    """Convert a pandas DataFrame to a dictionary with HTML and metadata."""
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = UPLOAD_DIR / f"{timestamp}_{file.filename}"
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    try:
        tables = read_pdf(
            str(file_path),
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

        return {
            "status": "success",
            "tables": tables_data,
            "message": f"Successfully extracted {len(tables)} tables",
            "file_id": timestamp,
        }
    except Exception as e:
        return {"status": "error", "message": f"Error processing PDF: {str(e)}"}
    finally:
        os.remove(file_path)


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
        return {"status": "error", "message": f"Error updating table: {str(e)}"}


@app.post("/download-table")
async def download_table(table_data: Dict = Body(...)):
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
        return {
            "status": "error",
            "message": f"Error preparing table for download: {str(e)}",
        }


@app.post("/merge-tables")
async def merge_tables(tables_data: List[Dict] = Body(...)):
    try:
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for i, table_data in enumerate(tables_data):
                df = pd.DataFrame(table_data['data'])

                sheet_name = f"Table {i+1}"
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(), len(str(col))
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2

        excel_data = output.getvalue()

        return {
            "status": "success",
            "excel_data": base64.b64encode(excel_data).decode(),
            "message": f"Successfully merged {len(tables_data)} tables",
        }
    except Exception as e:
        return {"status": "error", "message": f"Error merging tables: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
