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

def analyze_document_layout(file_bytes, file_name):
    """Analyze document using Azure Document Intelligence Layout Analysis only"""
    if not (AZURE_FORMRECOGNIZER_ENDPOINT and AZURE_FORMRECOGNIZER_KEY):
        st.error("Azure Document Intelligence credentials not set in .env.")
        return None, None, None
    
    client = DocumentAnalysisClient(
        endpoint=AZURE_FORMRECOGNIZER_ENDPOINT,
        credential=AzureKeyCredential(AZURE_FORMRECOGNIZER_KEY)
    )
    
    layout_tables = []
    merged_table = None
    key_value_pairs = []
    
    try:
        st.sidebar.info("🔍 Running Layout Analysis...")
        poller = client.begin_analyze_document("prebuilt-layout", file_bytes)
        layout_result = poller.result()
        st.sidebar.success("✅ Layout analysis completed")
        
        # Extract tables
        if hasattr(layout_result, "tables") and layout_result.tables:
            st.sidebar.info(f"📊 Found {len(layout_result.tables)} tables...")
            for idx, table in enumerate(layout_result.tables):
                page_num = table.bounding_regions[0].page_number if table.bounding_regions else 'Unknown'
                st.sidebar.info(f"📄 Processing table {idx+1}/{len(layout_result.tables)} (Page {page_num})")
                
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
                st.sidebar.info("🔗 Checking for table merging opportunities...")
                try:
                    # Check if all tables have the same number of columns
                    if all(len(df.columns) == len(layout_tables[0].columns) for df in layout_tables):
                        merged_table = pd.concat(layout_tables, ignore_index=True)
                        st.sidebar.success("✅ Tables merged successfully")
                    else:
                        st.sidebar.info("ℹ️ Tables have different structures - keeping separate")
                except Exception as e:
                    st.sidebar.warning(f"⚠️ Could not merge tables: {e}")
        else:
            st.sidebar.warning("⚠️ No tables found in layout analysis")
            
        # Extract key-value pairs
        if hasattr(layout_result, "key_value_pairs") and layout_result.key_value_pairs:
            st.sidebar.info(f"🔑 Found {len(layout_result.key_value_pairs)} key-value pairs...")
            for kv_pair in layout_result.key_value_pairs:
                if kv_pair.key and kv_pair.value:
                    key_content = kv_pair.key.content if kv_pair.key.content else ""
                    value_content = kv_pair.value.content if kv_pair.value.content else ""
                    if key_content.strip() and value_content.strip():
                        key_value_pairs.append({
                            'Key': key_content.strip(),
                            'Value': value_content.strip(),
                            'Confidence': round(kv_pair.confidence, 2) if hasattr(kv_pair, 'confidence') else 1.0
                        })
            st.sidebar.success(f"✅ Extracted {len(key_value_pairs)} key-value pairs")
        else:
            st.sidebar.warning("⚠️ No key-value pairs found in layout analysis")
            
    except Exception as e:
        st.sidebar.error(f"❌ Layout analysis failed: {e}")
        st.error(f"Layout analysis failed: {e}")
        return None, None, None
    
    st.sidebar.success("🎉 Layout analysis completed!")
    return layout_tables, merged_table, key_value_pairs

# Streamlit UI
st.set_page_config(page_title="Document Layout Analyzer", layout="wide")
st.title("📄 Document Layout Analyzer")
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
        type=['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff']
    )

# Check if file is selected
current_file = selected_file if file_source == "Azure Blob Storage" else (uploaded_file.name if uploaded_file else None)

# Only show the analyze button if a file is selected/uploaded
if current_file:
    if st.sidebar.button("🔍 Analyze Document"):
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
        
        # Run layout analysis
        layout_tables, merged_table, key_value_pairs = analyze_document_layout(file_bytes, file_name)
        
        # Display results
        if layout_tables or key_value_pairs:
            st.sidebar.markdown("---")
            st.sidebar.success("🎉 Analysis completed!")
            
            # Display tables
            if layout_tables:
                st.subheader("📊 Extracted Tables")
                
                if merged_table is not None:
                    st.write("**Merged Table (All Pages):**")
                    st.dataframe(merged_table, use_container_width=True)
                    
                    # Download options for merged table
                    csv_data = merged_table.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Merged Table as CSV",
                        data=csv_data,
                        file_name=f"{current_file}_merged_table.csv",
                        mime="text/csv"
                    )
                    
                    json_data = merged_table.to_json(orient='records', force_ascii=False, indent=2)
                    st.download_button(
                        label="📥 Download Merged Table as JSON",
                        data=json_data,
                        file_name=f"{current_file}_merged_table.json",
                        mime="application/json"
                    )
                else:
                    st.write(f"**Found {len(layout_tables)} separate tables:**")
                    for idx, df in enumerate(layout_tables):
                        with st.expander(f"Table {idx+1} ({len(df)} rows, {len(df.columns)} columns)"):
                            st.dataframe(df, use_container_width=True)
                            
                            # Download options for individual tables
                            csv_data = df.to_csv(index=False)
                            st.download_button(
                                label=f"📥 Download Table {idx+1} as CSV",
                                data=csv_data,
                                file_name=f"{current_file}_table_{idx+1}.csv",
                                mime="text/csv",
                                key=f"csv_{idx}"
                            )
            else:
                st.info("No tables found in the document.")
            
            # Display key-value pairs
            if key_value_pairs:
                st.subheader("🔑 Key-Value Pairs")
                st.write(f"**Found {len(key_value_pairs)} key-value pairs:**")
                
                kv_df = pd.DataFrame(key_value_pairs)
                st.dataframe(kv_df, use_container_width=True)
                
                # Download options for key-value pairs
                csv_data = kv_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Key-Value Pairs as CSV",
                    data=csv_data,
                    file_name=f"{current_file}_key_value_pairs.csv",
                    mime="text/csv"
                )
                
                json_data = kv_df.to_json(orient='records', force_ascii=False, indent=2)
                st.download_button(
                    label="📥 Download Key-Value Pairs as JSON",
                    data=json_data,
                    file_name=f"{current_file}_key_value_pairs.json",
                    mime="application/json"
                )
            else:
                st.info("No key-value pairs found in the document.")
        else:
            st.error("No data could be extracted from the document.")
else:
    st.sidebar.info("Please select or upload a file to analyze.")

# Information section
with st.expander("ℹ️ About Layout Analysis"):
    st.markdown("""
    **Azure Document Intelligence Layout Analysis** extracts:
    
    - **Tables**: Structured table data with rows and columns
    - **Key-Value Pairs**: Field names and their corresponding values
    - **Text**: Raw text content (not displayed in this app)
    - **Selection Marks**: Checkboxes and radio buttons
    
    This technique works best with:
    - Invoices, receipts, and forms
    - Structured documents with clear layouts
    - Documents with tables and form fields
    
    **Supported file formats**: PDF, PNG, JPG, JPEG, BMP, TIFF
    """)
