# Document Layout Analyzer

Extract tables and key-value pairs from documents using Azure Document Intelligence Layout Analysis. A clean, focused tool for structured data extraction from PDFs and images.

## Features
- **Azure Document Intelligence Layout Analysis**: Pure layout-based extraction without prebuilt models
- **Multiple File Sources**: Azure Blob Storage or local file upload
- **Table Extraction**: Automatically detects and extracts all tables from documents
- **Smart Table Merging**: Intelligently combines tables with similar structures
- **Key-Value Pairs**: Extracts form fields and their values with confidence scores
- **Clean Data Display**: Organized presentation of extracted data
- **Export Options**: Download results as CSV or JSON formats
- **Real-time Progress**: Sidebar progress tracking during analysis

## What It Extracts
- **Tables**: Structured table data with rows and columns
- **Key-Value Pairs**: Field names and their corresponding values (with confidence scores)
- **Form Data**: Automatically detected form fields and values
- **Multi-page Support**: Processes all pages and can merge related tables

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
