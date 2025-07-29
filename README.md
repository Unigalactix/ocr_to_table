


# Azure Blob OCR Data Viewer

Easily extract, view, and download tabular data from files stored in Azure Blob Storage or uploaded locally. Designed for invoices, receipts, and similar documents. Supports PDF, images, CSV, Excel, and JSON files.

---

## Folder Structure

- `app.py` — Main Streamlit application for file selection, extraction, and display
- `requirements.txt` — All required Python dependencies
- `README.md` — This documentation
- `.env` — Your Azure Blob Storage credentials (not tracked by git)
- `.gitignore` — Ignores `.env`, system files, and other non-essential files

---

## Features

- Connect to Azure Blob Storage using credentials from `.env` and (optionally) `tbudgetdb.json`
- Select files (PDF, images, CSV, Excel, JSON) from your Azure container
- **Upload local files** (CSV, Excel, JSON, PDF, images) for quick testing
- **Sheet selection** for Excel files
- **Pagination** and **column filtering/search** for large tables
- **Download error log** for troubleshooting
- **User feedback** (thumbs up/down) in sidebar
- **Session state** remembers last selections
- **Help/documentation link** in sidebar
- **OCR language selection** (multi-language OCR support)
- **Visualization**: Pie/bar charts for quick insights
- **Mobile responsive UI** (Streamlit layout hints)
- **Accessibility**: ARIA labels, screen reader hints
- **Performance note**: Async/background processing recommended for large files
- OCR support for PDF and image files (`pdfplumber`, `pytesseract`)
- Smart extraction: Only meaningful items/services and totals are shown; address/city/symbol-only labels are ignored
- Deduplication: No duplicate items in the table
- Subtotal and Total always shown at the bottom
- Download extracted table as CSV or JSON

---

## Setup

1. Clone the repository:
   ```sh
   git clone https://github.com/Unigalactix/ocr_to_table.git
   cd ocr_to_table
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Add your Azure Blob credentials to `.env`:
   ```env
   AZURE_BLOB_CONNECTION_STRING=your_connection_string_here
   AZURE_BLOB_KEY=your_key_here
   ```
4. (Optional) Add storage account info to `tbudgetdb.json` for default container/account info

---

## Usage

1. Run the app:
   ```sh
   streamlit run app.py
   # or
   python -m streamlit run app.py
   ```
2. Enter credentials if prompted
3. Select a file from the dropdown **or upload a local file**
4. For Excel files, select the sheet to view
5. Use the filter/search box above tables to find data quickly
6. Use pagination controls to browse large tables
7. Download the table as CSV or JSON
8. Download error log from the sidebar if needed
9. Provide feedback in the sidebar
11. Select OCR language in the sidebar for multi-language support
12. View charts/graphs for quick insights

---

## File Types Supported

- **PDF**: Extracts and previews tables for both uploads and blobs; falls back to OCR if no tables found. If no tables or text are found, a message is shown.
- **Images**: OCR extraction for tabular/summary data
- **CSV**: Loads and displays as-is
- **Excel (.xlsx, .xls)**: Loads all sheets, allows sheet selection
- **JSON**: Loads and displays as a table

---

## Notes

- Only meaningful items/services and totals are shown; address/city/symbol-only labels are ignored
- Works best with invoices, receipts, and similar structured documents
- For best OCR results, ensure Tesseract is installed and available in your system path
- For large files, async/background processing is recommended (see sidebar note)
- The UI is mobile-friendly and includes accessibility improvements for screen readers and keyboard navigation

---

## Dependencies

All dependencies are listed in `requirements.txt`:

- streamlit
- pandas
- python-dotenv
- azure-storage-blob
- pytesseract
- Pillow
- pdfplumber
- openpyxl
- streamlit-extras

---

## Security & .env

- **.env** is used for secrets and is ignored by git (see `.gitignore`). Never commit your credentials.
- Example:
  ```env
  AZURE_BLOB_CONNECTION_STRING=your_connection_string_here
  AZURE_BLOB_KEY=your_key_here
  ```

---

## License

MIT License

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
3. Select a file from the dropdown **or upload a local file**
4. For Excel files, select the sheet to view
5. For PDF uploads, tables will be previewed if found; otherwise, a message will be shown
5. Use the filter/search box above tables to find data quickly
6. Use pagination controls to browse large tables
7. Download the table as CSV or JSON (or download the raw file if format is not recognized)
8. Download error log from the sidebar if needed
9. Provide feedback in the sidebar
10. Select OCR language in the sidebar for multi-language support
11. View charts/graphs for quick insights

---


## Notes

- Only meaningful items/services and totals are shown; address/city/symbol-only labels are ignored
- Works best with invoices, receipts, and similar structured documents
- For best OCR results, ensure Tesseract is installed and available in your system path
- For large files, async/background processing is recommended (see sidebar note)
- The UI is mobile-friendly and includes accessibility improvements for screen readers and keyboard navigation

---


## Dependencies

- streamlit
- pandas
- python-dotenv
- azure-storage-blob
- pytesseract
- Pillow
- pdfplumber
- openpyxl
- streamlit-extras

---


## License

MIT License
