# Budget Table Extractor

A modular Streamlit application that extracts tables from documents using Azure Document Intelligence, with a focus on budget and financial data extraction.

## Features

- **Modular Architecture**: Clean separation of concerns with dedicated modules
- **Multiple File Sources**: Support for Azure Blob Storage and local file uploads
- **Document Processing**: Extract tables from PDFs and images using Azure Document Intelligence
- **Budget Focus**: Automatically identifies and prioritizes budget-related tables
- **Consolidated Output**: Merges all tables into a single consolidated view
- **Multiple Formats**: Support for PDF, images, CSV, and Excel files
- **Clean UI**: Minimal, emoji-free interface focused on functionality

## Project Structure

```
ocr_to_table/
├── main.py                 # Main application entry point (minimal)
├── config.py              # Azure configuration management
├── table_extractor.py     # Core table extraction logic
├── ui_handler.py          # Streamlit UI components
├── styles.css             # Optional CSS styling
├── utils/                 # Utility modules
│   ├── __init__.py
│   ├── currency_utils.py  # Budget/currency detection logic
│   ├── blob_manager.py    # Azure Blob Storage operations
│   └── file_utils.py      # File processing utilities
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from .env.example)
└── README.md
```

## Setup
1. Clone this repository or copy the files to your workspace.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Add your Azure credentials to `.env`:
   ```
   AZURE_BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
   AZURE_BLOB_KEY=your-blob-storage-key
   AZURE_BLOB_CONTAINER=your-container-name
   AZURE_FORMRECOGNIZER_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_FORMRECOGNIZER_KEY=your-document-intelligence-key
   ```

## Usage
1. Run the app:
   ```sh
   streamlit run app.py
   ```
2. Choose your file source (Azure Blob Storage or Local Upload)
3. Select a file from the dropdown or upload a local file
4. Click **🔍 Analyze Document** to start layout analysis
5. View extracted tables and key-value pairs
6. Download results as CSV or JSON if needed

## Supported Formats
- **PDF** files
- **Images**: PNG, JPG, JPEG, BMP, TIFF
## Dependencies
- streamlit
- pandas
- python-dotenv
- azure-storage-blob
- azure-ai-formrecognizer

## How It Works
- Uses Azure Document Intelligence **Layout Analysis** only
- No prebuilt models required - pure layout-based extraction
- Automatically detects table structures and form fields
- Provides confidence scores for key-value pairs
- Works best with structured documents (invoices, forms, reports)

## License
MIT
