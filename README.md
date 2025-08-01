# Azure Blob OCR Data Viewer

Easily extract, view, and download tabular data from files stored in Azure Blob Storage or uploaded locally. Designed for invoices, receipts, and similar documents. Supports PDF, images, CSV, Excel, and JSON files.

---
- **Download error log** for troubleshooting
- **Session state** remembers last selections
- **Help/documentation link** in sidebar
- **OCR language selection** (multi-language OCR support, legacy fallback)
- Smart extraction: Only meaningful items/services and totals are shown; address/city/symbol-only labels are ignored
- Subtotal and Total always shown at the bottom
- Download extracted table as CSV or JSON (always available for every table)

---

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

# Budget Extractor (OCR to Table)

This Streamlit app extracts tables and budget/total/amount fields from documents (PDFs, images, Excel, CSV, JSON) stored in Azure Blob Storage using Azure Document Intelligence. It provides a user-friendly UI for file selection, analysis, and table download.

## Features

- List files in Azure Blob Storage (main folder only)
- Select a file from the sidebar
- Click "RUN" to analyze the selected file
- For PDFs/images: runs Document Intelligence layout and prebuilt model analysis
- Extracts and displays only budget/total/amount fields from OCR and prebuilt models
- Shows detected tables and allows download as JSON
- For Excel, CSV, JSON: displays data directly

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following keys:
   ```env
   AZURE_BLOB_CONNECTION_STRING=your_blob_connection_string
   AZURE_BLOB_KEY=your_blob_key (optional, if not using connection string)
   AZURE_BLOB_CONTAINER=your_container_name
   AZURE_FORMRECOGNIZER_ENDPOINT=your_form_recognizer_endpoint
   AZURE_FORMRECOGNIZER_KEY=your_form_recognizer_key
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Select a file from the sidebar dropdown
2. Click the "RUN" button
3. For PDFs/images:
   - Extracted budget/total/amount fields are shown
   - Detected tables are displayed and can be downloaded as JSON
   - Prebuilt model results for budget/total/amount are shown if found
4. For Excel, CSV, JSON:
   - Data is displayed directly

## Notes

- Only files in the main folder of the container are listed
- Only budget/total/amount fields are extracted from OCR and prebuilt models
- Download buttons are provided for detected tables

## License

MIT
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
- opencv-python
- azure-ai-documentintelligence

---

## Security & .env

- **.env** is used for secrets and is ignored by git (see `.gitignore`). Never commit your credentials.
- Example:
  ```env
  # Azure Blob Storage
  AZURE_BLOB_CONNECTION_STRING=your_connection_string_here
  AZURE_BLOB_KEY=your_key_here

  # Azure Document Intelligence (Form Recognizer)
  AZURE_DOCUMENT_INTELLIGENCE_KEY=your_document_intelligence_key
  AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource-name.cognitiveservices.azure.com/
  AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID=your_model_id
  ```

---

## License

MIT License
