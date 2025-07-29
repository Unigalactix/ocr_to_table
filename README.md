# Azure Blob OCR Data Viewer

This Streamlit app allows you to connect to Azure Blob Storage, select files (PDF, images, CSV, Excel, JSON), and extract tabular data using OCR. It is designed for extracting and displaying item/service lists and totals from invoices, receipts, or similar documents.

## Features
- Connect to Azure Blob Storage using credentials from `.env` and `tbudgetdb.json`
- Select files from a container via dropdown
- OCR support for PDF and image files (using `pdfplumber` and `pytesseract`)
- Extracts and displays items/services and their amounts in a single table
- Deduplicates items, ignores address/city/symbol-only labels
- Always shows subtotal and total at the bottom of the table
- Download extracted table as CSV or JSON

## Setup
1. Clone this repository or copy the files to your workspace.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Add your Azure Blob credentials to `.env`:
   ```
   AZURE_BLOB_CONNECTION_STRING=...
   AZURE_BLOB_KEY=...
   ```
4. (Optional) Add storage account info to `tbudgetdb.json`.

## Usage
1. Run the app:
   ```sh
   streamlit run app.py
   ```
2. Enter your Azure Blob credentials if prompted.
3. Select a file from the dropdown.
4. Click **RUN** to extract and view data.
5. Download the table as CSV or JSON if needed.

## Notes
- Only meaningful items/services and totals are shown; address/city/symbol-only labels are ignored.
- Works best with invoices, receipts, and similar structured documents.
- For best OCR results, ensure Tesseract is installed and available in your system path.

## Dependencies
- streamlit
- pandas
- python-dotenv
- azure-storage-blob
- pytesseract
- Pillow
- pdfplumber

## License
MIT
