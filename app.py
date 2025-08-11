import os
import io
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import pandas as pd
import streamlit as st

# Load environment variables
load_dotenv()
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_KEY = os.getenv("AZURE_BLOB_KEY")
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "sampledocuments")
DOC_INTELLIGENCE_ENDPOINT = os.getenv("DOC_INTELLIGENCE_ENDPOINT")
DOC_INTELLIGENCE_KEY = os.getenv("DOC_INTELLIGENCE_KEY")

def get_blob_service_client():
    if AZURE_BLOB_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)
    elif AZURE_BLOB_KEY:
        st.warning("Connection string is preferred. Using key directly may not work for all setups.")
        return BlobServiceClient(account_url=f"https://{AZURE_BLOB_CONTAINER}.blob.core.windows.net", credential=AZURE_BLOB_KEY)
    else:
        st.error("No Azure Blob Storage credentials found in .env.")
        return None

def list_blobs_in_container(container_name):
    blob_service_client = get_blob_service_client()
    if not blob_service_client:
        return []
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blobs = container_client.list_blobs()
        return [blob.name for blob in blobs if '/' not in blob.name and '\\' not in blob.name]
    except Exception as e:
        st.error(f"Error listing blobs: {e}")
        return []

def download_blob_to_bytes(blob_name, container_name):
    blob_service_client = get_blob_service_client()
    if not blob_service_client:
        return None
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        return blob_client.download_blob().readall()
    except Exception as e:
        st.error(f"Error downloading blob '{blob_name}': {e}")
        return None

def is_csv_or_excel_file(file_name):
    """Check if the file is a CSV or Excel file"""
    file_extension = file_name.lower().split('.')[-1]
    return file_extension in ['csv', 'xlsx', 'xls']

def is_excel_file(file_name):
    """Check if the file is an Excel file"""
    file_extension = file_name.lower().split('.')[-1]
    return file_extension in ['xlsx', 'xls']

def generate_excel_column_names(num_columns):
    """Generate Excel-style column names (A, B, C, ..., AA, AB, etc.)"""
    columns = []
    for i in range(num_columns):
        col_name = ""
        temp = i
        while temp >= 0:
            col_name = chr(65 + (temp % 26)) + col_name
            temp = temp // 26 - 1
            if temp < 0:
                break
        columns.append(col_name)
    return columns

def read_csv_or_excel_file(file_bytes, file_name):
    """Read CSV or Excel file and return tables as DataFrames"""
    try:
        file_extension = file_name.lower().split('.')[-1]
        
        if file_extension == 'csv':
            # Read CSV file
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif file_extension in ['xlsx', 'xls']:
            # Read Excel file - handle multiple sheets
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
            sheets = {}
            for sheet_name in excel_file.sheet_names:
                # Read without header to get raw data
                sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                
                # Generate Excel-style column names (A, B, C, etc.)
                excel_columns = generate_excel_column_names(len(sheet_df.columns))
                sheet_df.columns = excel_columns
                
                # Set index to start from 1 (like Excel row numbers)
                sheet_df.index = range(1, len(sheet_df) + 1)
                
                sheets[sheet_name] = sheet_df
            
            if len(sheets) == 1:
                # Single sheet - return as single DataFrame
                df = list(sheets.values())[0]
            else:
                # Multiple sheets - return all sheets
                return list(sheets.values()), None, [], sheets
        else:
            return None, None, [], {}
        
        # For CSV files, also apply Excel-style formatting if no meaningful headers
        if file_extension == 'csv':
            # Check if first row looks like headers (all strings, no numbers)
            first_row = df.iloc[0] if len(df) > 0 else pd.Series()
            has_headers = all(isinstance(val, str) and not str(val).replace('.','').replace('-','').isdigit() for val in first_row if pd.notna(val))
            
            if not has_headers:
                # Generate Excel-style column names for CSV too
                excel_columns = generate_excel_column_names(len(df.columns))
                df.columns = excel_columns
                df.index = range(1, len(df) + 1)
        
        # Replace NaN values with empty strings for display
        df = df.fillna('')
        
        return [df], df, [], {}
        
    except Exception as e:
        st.error(f"Error reading {file_extension.upper()} file: {e}")
        return None, None, [], {}

def analyze_document_layout(file_bytes, file_name):
    """Analyze document using Azure Document Intelligence Layout Analysis only"""
    if not (DOC_INTELLIGENCE_ENDPOINT and DOC_INTELLIGENCE_KEY):
        st.error("Azure Document Intelligence credentials not set in .env.")
        return None, None, None
    
    client = DocumentAnalysisClient(
        endpoint=DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(DOC_INTELLIGENCE_KEY)
    )
    
    layout_tables = []
    merged_table = None
    key_value_pairs = []
    
    try:
        st.sidebar.info("Running Layout Analysis...")
        poller = client.begin_analyze_document("prebuilt-layout", file_bytes)
        layout_result = poller.result()
        st.sidebar.success("Layout analysis completed")
        
        # Extract tables
        if hasattr(layout_result, "tables") and layout_result.tables:
            st.sidebar.info(f"Found {len(layout_result.tables)} tables...")
            for idx, table in enumerate(layout_result.tables):
                page_num = table.bounding_regions[0].page_number if table.bounding_regions else 'Unknown'
                st.sidebar.info(f"Processing table {idx+1}/{len(layout_result.tables)} (Page {page_num})")
                
                rows = []
                for row_idx in range(table.row_count):
                    row = []
                    for col_idx in range(table.column_count):
                        cell = next((c for c in table.cells if c.row_index == row_idx and c.column_index == col_idx), None)
                        row.append(cell.content if cell else "")
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                layout_tables.append(df)
            
            # Try to merge tables if they have similar structure
            if layout_tables:
                st.sidebar.info("Checking for table merging opportunities...")
                try:
                    # Check if all tables have the same number of columns
                    if all(len(df.columns) == len(layout_tables[0].columns) for df in layout_tables):
                        merged_table = pd.concat(layout_tables, ignore_index=True)
                        st.sidebar.success("Tables merged successfully")
                    else:
                        st.sidebar.info("Tables have different structures - keeping separate")
                except Exception as e:
                    st.sidebar.warning(f"Could not merge tables: {e}")
        else:
            st.sidebar.warning("No tables found in layout analysis")
            
        # Extract key-value pairs
        if hasattr(layout_result, "key_value_pairs") and layout_result.key_value_pairs:
            st.sidebar.info(f"Found {len(layout_result.key_value_pairs)} key-value pairs...")
            for kv_pair in layout_result.key_value_pairs:
                if kv_pair.key and kv_pair.value:
                    key_content = kv_pair.key.content if kv_pair.key.content else ""
                    value_content = kv_pair.value.content if kv_pair.value.content else ""
                    if key_content.strip() and value_content.strip():
                        # Safe confidence extraction
                        confidence = 1.0
                        if hasattr(kv_pair, 'confidence') and kv_pair.confidence is not None:
                            confidence = round(kv_pair.confidence, 2)
                        
                        key_value_pairs.append({
                            'Key': key_content.strip(),
                            'Value': value_content.strip(),
                            'Confidence': confidence
                        })
            st.sidebar.success(f"Extracted {len(key_value_pairs)} key-value pairs")
        else:
            st.sidebar.warning("No key-value pairs found in layout analysis")
            
    except Exception as e:
        st.sidebar.error(f"Layout analysis failed: {e}")
        st.error(f"Layout analysis failed: {e}")
        return None, None, None
    
    st.sidebar.success("Layout analysis completed!")
    return layout_tables, merged_table, key_value_pairs

def analyze_document_invoice(file_bytes, file_name):
    """Analyze document using Azure Document Intelligence Invoice Analysis"""
    if not (DOC_INTELLIGENCE_ENDPOINT and DOC_INTELLIGENCE_KEY):
        st.error("Azure Document Intelligence credentials not set in .env.")
        return None, []
    
    client = DocumentAnalysisClient(
        endpoint=DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(DOC_INTELLIGENCE_KEY)
    )
    
    invoice_fields = []
    invoice_tables = []
    
    try:
        st.sidebar.info("Running Invoice Analysis...")
        poller = client.begin_analyze_document("prebuilt-invoice", file_bytes)
        invoice_result = poller.result()
        st.sidebar.success("Invoice analysis completed")
        
        # Extract invoice fields
        if hasattr(invoice_result, "documents") and invoice_result.documents:
            for doc in invoice_result.documents:
                if hasattr(doc, 'fields'):
                    for field_name, field in doc.fields.items():
                        if field and field.value is not None:
                            # Safe confidence extraction
                            confidence = 1.0
                            if hasattr(field, 'confidence') and field.confidence is not None:
                                confidence = round(field.confidence, 2)
                            
                            invoice_fields.append({
                                'Field': field_name,
                                'Value': str(field.value),
                                'Confidence': confidence,
                                'Source': 'Invoice Model'
                            })
        
        # Extract tables from invoice
        if hasattr(invoice_result, "tables") and invoice_result.tables:
            st.sidebar.info(f"Found {len(invoice_result.tables)} tables in invoice analysis...")
            for idx, table in enumerate(invoice_result.tables):
                rows = []
                for row_idx in range(table.row_count):
                    row = []
                    for col_idx in range(table.column_count):
                        cell = next((c for c in table.cells if c.row_index == row_idx and c.column_index == col_idx), None)
                        row.append(cell.content if cell else "")
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                invoice_tables.append(df)
        
        st.sidebar.success(f"Extracted {len(invoice_fields)} invoice fields")
        
    except Exception as e:
        st.sidebar.error(f"Invoice analysis failed: {e}")
        st.error(f"Invoice analysis failed: {e}")
        return None, []
    
    return invoice_fields, invoice_tables

def extract_amount_related_data(layout_kv_pairs, invoice_fields):
    """Extract budget and amount-related data from both analyses"""
    import re
    
    amount_data = []
    
    # Keywords that indicate amount/budget related fields
    amount_keywords = [
        'amount', 'total', 'sum', 'cost', 'price', 'budget', 'expense', 'fee', 
        'charge', 'payment', 'due', 'balance', 'subtotal', 'tax', 'discount',
        'invoice', 'bill', 'receipt', 'value', 'money', 'currency', 'dollar',
        'euro', 'pound', 'yen', 'credit', 'debit', 'net', 'gross'
    ]
    
    # Process layout analysis key-value pairs
    for kv in layout_kv_pairs:
        key_lower = kv['Key'].lower()
        value = kv['Value']
        
        # Check if key contains amount-related keywords
        if any(keyword in key_lower for keyword in amount_keywords):
            amount_data.append({
                'Label': kv['Key'],
                'Value': value,
                'Confidence': kv['Confidence'],
                'Source': 'Layout Analysis',
                'Type': 'Key-Value Pair'
            })
        
        # Check if value looks like a monetary amount (contains currency symbols or decimal patterns)
        if re.search(r'[\$€£¥₹]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*[\$€£¥₹]|\d+\.\d{2}', value):
            amount_data.append({
                'Label': kv['Key'],
                'Value': value,
                'Confidence': kv['Confidence'],
                'Source': 'Layout Analysis',
                'Type': 'Monetary Value'
            })
    
    # Process invoice analysis fields
    for field in invoice_fields:
        field_name = field['Field']
        value = field['Value']
        
        # Check if field is amount-related
        if any(keyword in field_name.lower() for keyword in amount_keywords):
            amount_data.append({
                'Label': field_name,
                'Value': value,
                'Confidence': field['Confidence'],
                'Source': 'Invoice Model',
                'Type': 'Invoice Field'
            })
        
        # Check if value looks like a monetary amount
        if re.search(r'[\$€£¥₹]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*[\$€£¥₹]|\d+\.\d{2}', str(value)):
            amount_data.append({
                'Label': field_name,
                'Value': value,
                'Confidence': field['Confidence'],
                'Source': 'Invoice Model',
                'Type': 'Monetary Value'
            })
    
    return amount_data

def create_final_budget_table(amount_data, layout_tables, invoice_tables):
    """Create final table with best outputs from both analyses, avoiding duplicates"""
    
    # Remove duplicates based on similar labels and values
    seen_combinations = set()
    deduplicated_data = []
    
    for item in amount_data:
        # Create a normalized key for duplicate detection
        normalized_key = (
            item['Label'].lower().strip(),
            str(item['Value']).lower().strip()
        )
        
        if normalized_key not in seen_combinations:
            seen_combinations.add(normalized_key)
            deduplicated_data.append(item)
        else:
            # If duplicate found, keep the one with higher confidence
            existing_item = next((x for x in deduplicated_data 
                                if (x['Label'].lower().strip(), str(x['Value']).lower().strip()) == normalized_key), None)
            if existing_item and item['Confidence'] > existing_item['Confidence']:
                deduplicated_data.remove(existing_item)
                deduplicated_data.append(item)
    
    # Sort by confidence score (highest first)
    deduplicated_data.sort(key=lambda x: x['Confidence'], reverse=True)
    
    # Create final DataFrame
    final_df = pd.DataFrame(deduplicated_data)
    
    # Combine table data from both analyses
    all_tables = []
    if layout_tables:
        for i, table in enumerate(layout_tables):
            table_copy = table.copy()
            table_copy['Table_Source'] = f'Layout_Table_{i+1}'
            all_tables.append(table_copy)
    
    if invoice_tables:
        for i, table in enumerate(invoice_tables):
            table_copy = table.copy()
            table_copy['Table_Source'] = f'Invoice_Table_{i+1}'
            all_tables.append(table_copy)
    
    return final_df, all_tables

# Streamlit UI
st.set_page_config(page_title="Document Layout Analyzer", layout="wide")
st.title("Document Layout Analyzer")
st.markdown("*Extract tables and key-value pairs using Azure Document Intelligence Layout Analysis*")

# File source selection
file_source = st.sidebar.radio("Choose file source:", ["Azure Blob Storage", "Local Upload"])

selected_file = None
uploaded_file = None

if file_source == "Azure Blob Storage":
    st.sidebar.header("Azure Blob Storage")
    blob_files = list_blobs_in_container(AZURE_BLOB_CONTAINER)
    if blob_files:
        selected_file = st.sidebar.selectbox("Select a file to process:", blob_files)
    else:
        st.sidebar.warning("No files found in the container.")
else:
    st.sidebar.header("Local File Upload")
    uploaded_file = st.sidebar.file_uploader(
        "Choose a file to upload",
        type=['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'csv', 'xlsx', 'xls']
    )

# Check if file is selected
current_file = selected_file if file_source == "Azure Blob Storage" else (uploaded_file.name if uploaded_file else None)

# Only show the analyze button if a file is selected/uploaded
if current_file:
    if st.sidebar.button("Analyze Document"):
        st.info(f"Processing: {current_file}")
        
        # Clear previous analysis status
        st.sidebar.markdown("---")
        st.sidebar.subheader("Analysis Progress")
        
        # Get file bytes based on source
        if file_source == "Azure Blob Storage":
            st.sidebar.info("Downloading file from Azure Blob Storage...")
            file_bytes = download_blob_to_bytes(selected_file, AZURE_BLOB_CONTAINER)
            if not file_bytes:
                st.error("Could not download the selected file.")
                st.stop()
            file_name = selected_file
            st.sidebar.success("File downloaded successfully")
        else:  # Local upload
            st.sidebar.info("Reading uploaded file...")
            file_bytes = uploaded_file.read()
            file_name = uploaded_file.name
            st.sidebar.success("File read successfully")
        
        # Check file type and handle accordingly
        if is_excel_file(file_name):
            # Excel files: Skip all analysis, process directly
            st.sidebar.info(f"Detected Excel file - processing directly (skipping layout analysis)...")
            layout_tables, merged_table, key_value_pairs, sheets = read_csv_or_excel_file(file_bytes, file_name)
            st.sidebar.success("Excel file processed successfully!")
            invoice_fields = []
            final_budget_table = None
            all_combined_tables = []
        elif is_csv_or_excel_file(file_name):  # This will catch CSV files
            # CSV files: Process directly but could add analysis later if needed
            st.sidebar.info(f"Detected CSV file - processing directly...")
            layout_tables, merged_table, key_value_pairs, sheets = read_csv_or_excel_file(file_bytes, file_name)
            st.sidebar.success("CSV file processed successfully!")
            invoice_fields = []
            final_budget_table = None
            all_combined_tables = []
        else:
            # Run both layout and invoice analysis for other file types
            layout_tables, merged_table, key_value_pairs = analyze_document_layout(file_bytes, file_name)
            invoice_fields, invoice_tables = analyze_document_invoice(file_bytes, file_name)
            sheets = {}
            
            # Extract amount-related data and create final budget table
            if layout_tables or invoice_fields:
                st.sidebar.info("Creating final budget table...")
                amount_data = extract_amount_related_data(key_value_pairs, invoice_fields)
                final_budget_table, all_combined_tables = create_final_budget_table(amount_data, layout_tables, invoice_tables)
                st.sidebar.success("Final budget table created!")
            else:
                final_budget_table = None
                all_combined_tables = []
        
        # Display results
        if layout_tables or key_value_pairs or sheets or final_budget_table is not None:
            st.sidebar.markdown("---")
            st.sidebar.success("Analysis completed!")
            
            # Display Final Budget Table (Priority Display)
            if final_budget_table is not None and not final_budget_table.empty:
                st.subheader("🎯 Final Budget & Amount Analysis")
                st.write("**Combined results from Layout Analysis and Invoice Model (duplicates removed)**")
                
                # Replace NaN values with empty strings for display
                display_budget = final_budget_table.fillna('')
                st.dataframe(display_budget, use_container_width=True)
                
                # Only JSON download for final table as requested
                json_data = final_budget_table.to_json(orient='records', force_ascii=False, indent=2)
                st.download_button(
                    label="📥 Download Final Budget Table as JSON",
                    data=json_data,
                    file_name=f"{current_file}_final_budget_analysis.json",
                    mime="application/json",
                    key="final_budget_json"
                )
                
                st.markdown("---")
            
            # Display Comparison Section (only for documents that were analyzed)
            if not is_csv_or_excel_file(file_name) and (key_value_pairs or invoice_fields):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 Layout Analysis Results")
                    if key_value_pairs:
                        st.write(f"**Found {len(key_value_pairs)} key-value pairs:**")
                        layout_kv_df = pd.DataFrame(key_value_pairs)
                        st.dataframe(layout_kv_df.fillna(''), use_container_width=True)
                    else:
                        st.info("No key-value pairs found in layout analysis.")
                
                with col2:
                    st.subheader("🧾 Invoice Model Results")
                    if invoice_fields:
                        st.write(f"**Found {len(invoice_fields)} invoice fields:**")
                        invoice_df = pd.DataFrame(invoice_fields)
                        st.dataframe(invoice_df.fillna(''), use_container_width=True)
                    else:
                        st.info("No invoice fields found in invoice analysis.")
                
                st.markdown("---")
            
            # Display Excel sheets if available
            if sheets:
                st.subheader("📊 Excel Sheets")
                if is_excel_file(file_name):
                    st.info("📝 **Excel Format Applied**: Columns are labeled with letters (A, B, C...) and rows with numbers (1, 2, 3...) like Microsoft Excel")
                
                for sheet_name, sheet_df in sheets.items():
                    with st.expander(f"Sheet: {sheet_name} ({len(sheet_df)} rows, {len(sheet_df.columns)} columns)"):
                        # Replace NaN values with empty strings for display
                        display_df = sheet_df.fillna('')
                        st.dataframe(display_df, use_container_width=True)
                        
                        # Download options for individual sheets
                        csv_data = sheet_df.to_csv(index=True)  # Include index for Excel files to show row numbers
                        st.download_button(
                            label=f"Download {sheet_name} as CSV",
                            data=csv_data,
                            file_name=f"{current_file}_{sheet_name}.csv",
                            mime="text/csv",
                            key=f"sheet_csv_{sheet_name}"
                        )
            
            # Display tables from both analyses
            if layout_tables or all_combined_tables:
                st.subheader("📑 Extracted Tables")
                
                if merged_table is not None:
                    st.write("**Layout Analysis - Merged Table:**")
                    # Replace NaN values with empty strings for display
                    display_merged = merged_table.fillna('')
                    st.dataframe(display_merged, use_container_width=True)
                elif layout_tables:
                    st.write(f"**Layout Analysis - Found {len(layout_tables)} separate tables:**")
                    for idx, df in enumerate(layout_tables):
                        with st.expander(f"Layout Table {idx+1} ({len(df)} rows, {len(df.columns)} columns)"):
                            # Replace NaN values with empty strings for display
                            display_df = df.fillna('')
                            st.dataframe(display_df, use_container_width=True)
                
                # Display combined tables from both analyses
                if all_combined_tables:
                    st.write("**Combined Tables from Both Analyses:**")
                    for idx, table in enumerate(all_combined_tables):
                        source = table['Table_Source'].iloc[0] if 'Table_Source' in table.columns else f"Table_{idx+1}"
                        table_display = table.drop('Table_Source', axis=1) if 'Table_Source' in table.columns else table
                        with st.expander(f"{source} ({len(table_display)} rows, {len(table_display.columns)} columns)"):
                            display_df = table_display.fillna('')
                            st.dataframe(display_df, use_container_width=True)
            
            else:
                if not sheets and (final_budget_table is None or final_budget_table.empty):
                    st.info("No tables or structured data found in the document.")
                    
                    # Download options for merged table
                    csv_data = merged_table.to_csv(index=False)
                    st.download_button(
                        label="Download Merged Table as CSV",
                        data=csv_data,
                        file_name=f"{current_file}_merged_table.csv",
                        mime="text/csv"
                    )
                    
                    json_data = merged_table.to_json(orient='records', force_ascii=False, indent=2)
                    st.download_button(
                        label="Download Merged Table as JSON",
                        data=json_data,
                        file_name=f"{current_file}_merged_table.json",
                        mime="application/json"
                    )
                else:
                    st.write(f"**Found {len(layout_tables)} separate tables:**")
                    for idx, df in enumerate(layout_tables):
                        with st.expander(f"Table {idx+1} ({len(df)} rows, {len(df.columns)} columns)"):
                            # Replace NaN values with empty strings for display
                            display_df = df.fillna('')
                            st.dataframe(display_df, use_container_width=True)
                            
                # Display combined tables from both analyses
                if all_combined_tables:
                    st.write("**Combined Tables from Both Analyses:**")
                    for idx, table in enumerate(all_combined_tables):
                        source = table['Table_Source'].iloc[0] if 'Table_Source' in table.columns else f"Table_{idx+1}"
                        table_display = table.drop('Table_Source', axis=1) if 'Table_Source' in table.columns else table
                        with st.expander(f"{source} ({len(table_display)} rows, {len(table_display.columns)} columns)"):
                            display_df = table_display.fillna('')
                            st.dataframe(display_df, use_container_width=True)
            
            # Show message if no data found
            if not sheets and (final_budget_table is None or final_budget_table.empty) and not layout_tables:
                st.info("No tables or structured data found in the document.")
        else:
            st.error("No data could be extracted from the document.")
else:
    st.sidebar.info("Please select or upload a file to analyze.")

# Information section
with st.expander("About Document Analysis"):
    st.markdown("""
    **Azure Document Intelligence with Dual Analysis** extracts:
    
    - **Layout Analysis**: Tables, key-value pairs, and structured content
    - **Invoice Analysis**: Specialized invoice field extraction
    - **Final Budget Table**: Combined, deduplicated amount and budget-related data
    
    **File Type Handling**:
    - **Excel Files (.xlsx, .xls)**: 
      - ✅ **Layout Analysis SKIPPED** (processed directly)
      - ✅ **Excel-style formatting**: Columns as letters (A, B, C...), rows as numbers (1, 2, 3...)
      - ✅ **Multi-sheet support**: Each sheet displayed separately
      - ✅ **Null values shown as empty cells**
    - **CSV Files**: Displayed as-is with optional Excel-style column naming
    - **Documents (PDF, Images)**: Full dual analysis (Layout + Invoice models)
    
    **For documents (PDF, images)**, the app runs both analyses and creates:
    - A comparison view of both analysis results
    - A final budget table with the best data from both sources
    - Automatic deduplication and confidence-based selection
    
    This technique works best with:
    - Invoices, receipts, and forms
    - Budget documents and financial statements
    - Structured documents with clear layouts
    - Excel files for direct data viewing with proper formatting
    
    **Supported file formats**: PDF, PNG, JPG, JPEG, BMP, TIFF, CSV, XLSX, XLS
    """)
