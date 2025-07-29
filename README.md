

# Azure Blob OCR Data Viewer

Easily extract and view tabular data from files stored in Azure Blob Storage using OCR. Designed for invoices, receipts, and similar documents.

---

## Features

- Connect to Azure Blob Storage using credentials from `.env` and `tbudgetdb.json`
- Select files (PDF, images, CSV, Excel, JSON) from your container
- OCR support for PDF and image files (`pdfplumber`, `pytesseract`)
- Smart extraction: Only meaningful items/services and totals are shown; address/city/symbol-only labels are ignored
- Deduplication: No duplicate items in the table
- Subtotal and Total always shown at the bottom
- Download extracted table as CSV or JSON

---

## Setup

1. Clone the repository
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Add your Azure Blob credentials to `.env`:
   ```env
   AZURE_BLOB_CONNECTION_STRING=your_connection_string_here
   AZURE_BLOB_KEY=your_key_here
   ```
4. (Optional) Add storage account info to `tbudgetdb.json`

---

## Usage

1. Run the app:
   ```sh
   streamlit run app.py
   OR
   python -m streamlit run app.py 
   ```
2. Enter credentials if prompted
3. Select a file from the dropdown
4. Click RUN to extract and view data
5. Download the table as CSV or JSON

---

## Notes

- Only meaningful items/services and totals are shown; address/city/symbol-only labels are ignored
- Works best with invoices, receipts, and similar structured documents
- For best OCR results, ensure Tesseract is installed and available in your system path

---

## Dependencies

- streamlit
- pandas
- python-dotenv
- azure-storage-blob
- pytesseract
- Pillow
- pdfplumber

---

## License

MIT License
