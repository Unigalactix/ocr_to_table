

import os
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
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "budget-docs")
AZURE_FORMRECOGNIZER_ENDPOINT = os.getenv("AZURE_FORMRECOGNIZER_ENDPOINT")
AZURE_FORMRECOGNIZER_KEY = os.getenv("AZURE_FORMRECOGNIZER_KEY")

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

def analyze_with_document_intelligence(file_bytes, file_name):
    if not (AZURE_FORMRECOGNIZER_ENDPOINT and AZURE_FORMRECOGNIZER_KEY):
        st.error("Azure Document Intelligence credentials not set in .env.")
        return None, None
    client = DocumentAnalysisClient(
        endpoint=AZURE_FORMRECOGNIZER_ENDPOINT,
        credential=AzureKeyCredential(AZURE_FORMRECOGNIZER_KEY)
    )
    # 1. Layout analysis (extract budget/total/amount from tables only)
    layout_budget = []
    layout_tables = []
    merged_table = None
    try:
        st.sidebar.info("🔍 Starting layout analysis...")
        poller = client.begin_analyze_document("prebuilt-layout", file_bytes)
        layout_result = poller.result()
        st.sidebar.success("✅ Layout analysis completed")
        # Process all tables from all pages
        if hasattr(layout_result, "tables") and layout_result.tables:
            st.sidebar.info(f"📊 Processing {len(layout_result.tables)} tables from layout...")
            for idx, table in enumerate(layout_result.tables):
                st.sidebar.info(f"📄 Processing table {idx+1}/{len(layout_result.tables)} (Page {table.bounding_regions[0].page_number if table.bounding_regions else 'Unknown'})")
                rows = []
                for row_idx in range(table.row_count):
                    row = []
                    for col_idx in range(table.column_count):
                        cell = next((c for c in table.cells if c.row_index == row_idx and c.column_index == col_idx), None)
                        row.append(cell.content if cell else "")
                    rows.append(row)
                df = pd.DataFrame(rows)
                layout_tables.append(df)
                # Search for budget/total/amount in table with comprehensive keywords
                budget_keywords = [
                    "budget", "total", "amount", "grand total", "net amount", "sub-total", "subtotal", 
                    "sub total", "final total", "overall total", "total amount", "total cost", 
                    "total price", "sum", "budget amount", "budget total", "cost", "price", 
                    "invoice total", "bill total", "payment", "due", "balance", "gross", 
                    "net", "final", "overall", "aggregate", "cumulative", "grand sum"
                ]
                
                # Priority keywords for final budget (higher priority = more likely to be final budget)
                final_budget_keywords = [
                    "grand total", "final total", "overall total", "total amount", "net amount",
                    "invoice total", "bill total", "total", "amount", "balance", "due"
                ]
                
                for r in rows:
                    for i, cell in enumerate(r):
                        cell_str = str(cell).lower().strip()
                        if any(kw in cell_str for kw in budget_keywords):
                            # Look for value in next cell or same row
                            value = r[i+1] if i+1 < len(r) else None
                            # Also check if current cell contains both label and value
                            if value is None and any(char.isdigit() for char in str(cell)):
                                value = cell
                            
                            # Determine priority based on keywords
                            priority = 0
                            for idx, final_kw in enumerate(final_budget_keywords):
                                if final_kw in cell_str:
                                    priority = len(final_budget_keywords) - idx  # Higher number = higher priority
                                    break
                            
                            layout_budget.append((cell, value, priority))
                for col in df.columns:
                    col_data = df[col].astype(str).str.lower()
                    for idx2, val in enumerate(col_data):
                        val_str = str(val).lower().strip()
                        if any(kw in val_str for kw in budget_keywords):
                            # Look for value in next column or same cell
                            value = df.iloc[idx2, col+1] if col+1 < df.shape[1] else None
                            # Also check if current cell contains both label and value
                            if value is None and any(char.isdigit() for char in str(val)):
                                value = val
                            
                            # Determine priority based on keywords
                            priority = 0
                            for idx, final_kw in enumerate(final_budget_keywords):
                                if final_kw in val_str:
                                    priority = len(final_budget_keywords) - idx  # Higher number = higher priority
                                    break
                            
                            layout_budget.append((val, value, priority))
            # Merge related tables: if all tables have the same columns, concatenate them
            if layout_tables:
                st.sidebar.info("🔗 Checking for table merging opportunities...")
                first_cols = [tuple(df.columns) for df in layout_tables]
                if all(cols == first_cols[0] for cols in first_cols):
                    merged_table = pd.concat(layout_tables, ignore_index=True)
                    st.sidebar.success("✅ Tables merged successfully")
                else:
                    merged_table = None
                    st.sidebar.info("ℹ️ Tables have different structures - keeping separate")
        else:
            st.sidebar.warning("⚠️ No tables found in layout analysis")
    except Exception as e:
        st.sidebar.error(f"❌ Layout analysis failed: {e}")
        st.error(f"Layout analysis failed: {e}")

    # Determine the best prebuilt model based on layout analysis content
    def determine_best_model(layout_tables, file_name):
        """Determine the best prebuilt model based on content analysis"""
        # Start with file name hints
        if any(x in file_name.lower() for x in ["invoice"]):
            base_model = "prebuilt-invoice"
        elif any(x in file_name.lower() for x in ["receipt"]):
            base_model = "prebuilt-receipt"
        else:
            base_model = "prebuilt-document"
        
        # Analyze content from layout tables for better model selection
        if layout_tables:
            all_text = ""
            for df in layout_tables:
                all_text += " " + " ".join(df.astype(str).values.flatten())
            all_text = all_text.lower()
            
            # Invoice indicators
            invoice_indicators = ["invoice", "bill to", "ship to", "invoice number", "invoice date", 
                                "vendor", "customer", "tax", "vat", "subtotal", "line item"]
            invoice_score = sum(1 for indicator in invoice_indicators if indicator in all_text)
            
            # Receipt indicators  
            receipt_indicators = ["receipt", "store", "cashier", "register", "purchase", "transaction",
                                "change", "cash", "card", "tender"]
            receipt_score = sum(1 for indicator in receipt_indicators if indicator in all_text)
            
            # Choose model with highest score
            if invoice_score > receipt_score and invoice_score >= 2:
                return "prebuilt-invoice"
            elif receipt_score >= 2:
                return "prebuilt-receipt"
        
        return base_model

    # 2. Prebuilt model (intelligently selected based on layout analysis)
    model_budget = []
    model_id = determine_best_model(layout_tables, file_name)
    st.sidebar.info(f"🧠 Intelligent model selection: {model_id}")
    
    st.sidebar.info(f"🤖 Starting prebuilt model analysis ({model_id})...")
    try:
        poller = client.begin_analyze_document(model_id, file_bytes)
        result = poller.result()
        st.sidebar.success(f"✅ Prebuilt model analysis completed")
        
        if hasattr(result, "documents") and result.documents:
            st.sidebar.info(f"📋 Processing {len(result.documents)} document(s) from prebuilt model...")
            doc = result.documents[0]
            budget_keywords = [
                "budget", "total", "amount", "grand total", "net amount", "sub-total", "subtotal", 
                "sub total", "final total", "overall total", "total amount", "total cost", 
                "total price", "sum", "budget amount", "budget total", "cost", "price", 
                "invoice total", "bill total", "payment", "due", "balance", "gross", 
                "net", "final", "overall", "aggregate", "cumulative", "grand sum"
            ]
            for k, v in doc.fields.items():
                k_lower = k.lower().strip()
                if any(kw in k_lower for kw in budget_keywords):
                    val = v.value if hasattr(v, "value") else v
                    model_budget.append((k, val))
            
            if model_budget:
                st.sidebar.success(f"✅ Found {len(model_budget)} budget-related field(s) in prebuilt model")
            else:
                st.sidebar.warning("⚠️ No budget fields found in prebuilt model")
        else:
            st.sidebar.warning("⚠️ No documents found in prebuilt model results")
    except Exception as e:
        st.sidebar.error(f"❌ Prebuilt model analysis failed: {e}")
        st.error(f"Prebuilt model analysis failed: {e}")

    st.sidebar.success("🎉 Document analysis completed!")
    
    # Extract the final budget value (highest priority)
    final_budget = None
    if layout_budget:
        # Sort by priority (highest first) and get the top result
        layout_budget.sort(key=lambda x: x[2], reverse=True)
        final_budget = layout_budget[0]  # (label, value, priority)
    
    return final_budget, layout_tables, model_budget, model_id, merged_table

st.set_page_config(page_title="Budget Extractor", layout="centered")
st.title("Budget Extractor")

# File source selection
file_source = st.sidebar.radio("Choose file source:", ["Azure Blob Storage", "Local Upload"])

selected_file = None
uploaded_file = None
file_bytes = None

if file_source == "Azure Blob Storage":
    st.sidebar.header("Azure Blob Storage")
    blob_files = list_blobs_in_container(AZURE_BLOB_CONTAINER)
    selected_file = st.sidebar.selectbox("Select a file to process:", blob_files)
else:
    st.sidebar.header("Local File Upload")
    uploaded_file = st.sidebar.file_uploader(
        "Choose a file to upload",
        type=['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'xlsx', 'xls', 'csv', 'json']
    )

# Check if file is already processed to show appropriate button text
current_file = selected_file if file_source == "Azure Blob Storage" else (uploaded_file.name if uploaded_file else None)
cache_key = f"processed_{current_file}" if current_file else None
is_processed = cache_key and cache_key in st.session_state
button_text = "RE-RUN" if is_processed else "RUN"

# Only show the run button if a file is selected/uploaded
if current_file:
    run_analysis = st.sidebar.button(button_text)
else:
    run_analysis = False
    st.sidebar.info("Please select or upload a file to process.")

if current_file and run_analysis:
    st.info(f"Processing: {current_file}")
    
    # Clear previous analysis status
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Analysis Progress")
    
    # Get file bytes based on source
    if file_source == "Azure Blob Storage":
        st.sidebar.info("📥 Downloading file from Azure Blob Storage...")
        file_bytes = download_blob_to_bytes(selected_file, AZURE_BLOB_CONTAINER)
        if not file_bytes:
            st.error("Could not download the selected file.")
            st.stop()
        file_name = selected_file
        st.sidebar.success("✅ File downloaded successfully")
    else:  # Local upload
        st.sidebar.info("📁 Reading uploaded file...")
        file_bytes = uploaded_file.read()
        file_name = uploaded_file.name
        st.sidebar.success("✅ File read successfully")
    
    # Show selected prebuilt model in sidebar during processing
    ext = os.path.splitext(file_name)[1].lower()
    if ext in [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
        st.sidebar.info("🔍 Will analyze layout first, then select optimal prebuilt model")
    
    use_cache = False  # Always reprocess when button is clicked
    final_budget, layout_tables, model_budget, model_id = None, None, None, None
    excel_sheets, csv_df, json_data = None, None, None
    
    if ext in [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
        st.sidebar.info("🔍 Starting Document Intelligence analysis...")
        final_budget, layout_tables, model_budget, model_id, merged_table = analyze_with_document_intelligence(file_bytes, file_name)
    elif ext in [".xlsx", ".xls"]:
        st.sidebar.info("📊 Processing Excel file...")
        try:
            import openpyxl
            import io
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            excel_sheets = {}
            for sheetname in wb.sheetnames:
                ws = wb[sheetname]
                rows = [row for row in ws.iter_rows(values_only=True)]
                df = pd.DataFrame(rows)
                excel_sheets[sheetname] = df
            st.sidebar.success(f"✅ Excel file processed - {len(excel_sheets)} sheet(s) found")
        except Exception as e:
            st.sidebar.error(f"❌ Excel processing failed: {e}")
            st.error(f"Error reading Excel file: {e}")
    elif ext == ".csv":
        st.sidebar.info("📄 Processing CSV file...")
        try:
            import io
            import csv
            reader = csv.reader(io.StringIO(file_bytes.decode('utf-8')))
            rows = [row for row in reader]
            csv_df = pd.DataFrame(rows)
            st.sidebar.success(f"✅ CSV file processed - {len(csv_df)} rows found")
        except Exception as e:
            st.sidebar.error(f"❌ CSV processing failed: {e}")
            st.error(f"Error reading CSV file: {e}")
    elif ext == ".json":
        st.sidebar.info("🔧 Processing JSON file...")
        try:
            import json
            json_data = json.loads(file_bytes.decode('utf-8'))
            st.sidebar.success("✅ JSON file processed successfully")
        except Exception as e:
            st.sidebar.error(f"❌ JSON processing failed: {e}")
            st.error(f"Error reading JSON file: {e}")
    
    # Final status
    st.sidebar.markdown("---")
    st.sidebar.success("🎉 All processing completed!")
    
    # Update cache with new results
    st.session_state[cache_key] = {
        'ext': ext,
        'final_budget': final_budget,
        'layout_tables': layout_tables,
        'model_budget': model_budget,
        'model_id': model_id,
        'merged_table': merged_table,
        'excel_sheets': excel_sheets,
        'csv_df': csv_df,
        'json_data': json_data
    }

    # Display results from cache or fresh
    if ext in [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
        st.subheader("Final Budget Amount")
        if final_budget:
            label, value, priority = final_budget
            st.write(f"**{label}**: {value}")
            st.info(f"Confidence: High (Priority score: {priority})")
        else:
            st.write("No final budget amount found in layout tables.")
        st.subheader("Detected Tables (Layout)")
        if merged_table is not None:
            st.write("Merged Table (All Pages)")
            st.dataframe(merged_table)
            json_data = merged_table.to_json(orient='records', force_ascii=False, indent=2)
            st.download_button(
                label="Download Merged Table as JSON",
                data=json_data,
                file_name=f"{current_file}_merged_table.json",
                mime="application/json"
            )
        elif layout_tables:
            for idx, df in enumerate(layout_tables):
                st.write(f"Table {idx+1}")
                st.dataframe(df)
                json_data = df.to_json(orient='records', force_ascii=False, indent=2)
                st.download_button(
                    label=f"Download Table {idx+1} as JSON",
                    data=json_data,
                    file_name=f"{current_file}_table{idx+1}.json",
                    mime="application/json"
                )
        else:
            st.write("No tables detected in layout.")
        if model_budget:
            st.subheader(f"Extracted Budget/Total/Amount (Prebuilt Model: {model_id})")
            for label, value in model_budget:
                st.write(f"{label}: {value}")
    elif ext in [".xlsx", ".xls"]:
        st.subheader("Excel file detected. Showing data directly:")
        if excel_sheets:
            for sheetname, df in excel_sheets.items():
                st.write(f"Sheet: {sheetname}")
                st.dataframe(df)
        else:
            st.write("No data found in Excel file.")
    elif ext == ".csv":
        st.subheader("CSV file detected. Showing data directly:")
        if csv_df is not None:
            st.dataframe(csv_df)
        else:
            st.write("No data found in CSV file.")
    elif ext == ".json":
        st.subheader("JSON file detected. Showing data directly:")
        if json_data is not None:
            st.json(json_data)
        else:
            st.write("No data found in JSON file.")
    else:
        st.warning(f"Unsupported file type: {ext}")
