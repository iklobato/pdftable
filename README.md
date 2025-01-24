# PDF Table Extractor

A professional FastAPI application that extracts tables from PDF files and displays them in a clean, modern interface.

## Features

- Drag and drop PDF file upload
- Extract all tables from PDF files
- Responsive Bootstrap UI
- Real-time processing feedback
- Clean table display with Bootstrap styling

## Requirements

- Python 3.7+
- FastAPI
- tabula-py
- pandas
- Java Runtime Environment (JRE) - Required for tabula-py

## Installation

1. Install the required Python packages:
```bash
pip install fastapi uvicorn python-multipart jinja2 tabula-py pandas
```

2. Make sure you have Java Runtime Environment (JRE) installed on your system.

## Running the Application

1. Navigate to the project directory:
```bash
cd pdf_table_extractor
```

2. Start the FastAPI server:
```bash
python main.py
```

3. Open your browser and visit `http://localhost:8000`

## Usage

1. Open the web interface in your browser
2. Either drag and drop a PDF file or click "Browse File" to select one
3. Wait for the processing to complete
4. View the extracted tables in a clean, formatted layout

## Notes

- The application processes all pages of the PDF file
- Tables are displayed with pagination and search functionality
- Uploaded files are automatically cleaned up after processing