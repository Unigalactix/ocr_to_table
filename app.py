
import streamlit as st
import pandas as pd
import time # For simulating connection delay
import json
import os
import io
import logging
from streamlit_extras.dataframe_explorer import dataframe_explorer



st.markdown(
    "<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True
)
# --- Load storage account info from tbudgetdb.json ---
json_path = "tbudgetdb.json"
account_name = ""
blob_endpoint = ""
default_container = "budget-docs"  # fallback
if os.path.exists(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
        # Try to get account name and blob endpoint
        account_name = data.get("name", "")
        blob_endpoint = data.get("primaryEndpoints", {}).get("blob", "")
        # Try to get default container name if present
        # Look for a property named 'container', else fallback
        default_container = data.get("container", default_container)

# --- Load default key from .env ---
from dotenv import load_dotenv
load_dotenv()
default_key = os.getenv("AZURE_BLOB_KEY", "")


def run_connection_and_show_data(selected_path, ocr_lang='eng'):
    """
    Connects to Azure Blob Storage and reads a file of any format.
    """
    from azure.storage.blob import BlobServiceClient
    import io
    with st.spinner('Connecting to Azure Blob Storage... 💸'):
        time.sleep(1)
    try:
        blob_service_client = BlobServiceClient.from_connection_string(selected_path['connection_string'])
        blob_client = blob_service_client.get_blob_client(container=selected_path['container_name'], blob=selected_path['blob_name'])
        blob_data = blob_client.download_blob().readall()
        file_format = selected_path['file_format'].lower()
        # Defensive: handle empty files
        if not blob_data or (isinstance(blob_data, bytes) and len(blob_data) == 0):
            st.warning("The selected file is empty.")
            return None
        # OCR logic for any file format
        import pytesseract
        from PIL import Image
        import tempfile
        import pdfplumber
        import re
        import matplotlib.pyplot as plt
        ocr_text = None
        # PDF logic: extract tables as-is, then OCR for summary if needed
        if file_format == 'pdf' or selected_path['blob_name'].lower().endswith('.pdf'):
            import numpy as np
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                tmp_pdf.write(blob_data)
                tmp_pdf.flush()
                with pdfplumber.open(tmp_pdf.name) as pdf:
                    all_tables = []
                    for page in pdf.pages:
                        tables = page.extract_tables()
                        for table in tables:
                            # Convert to DataFrame and append if not empty
                            if len(table) > 1:
                                columns = table[0]
                                seen = set()
                                unique_columns = []
                                for col in columns:
                                    col_name = str(col) if col is not None else "Column"
                                    count = 1
                                    while col_name in seen:
                                        col_name = f"{col}_{count}"
                                        count += 1
                                    unique_columns.append(col_name)
                                    seen.add(col_name)
                                try:
                                    df_table = pd.DataFrame(table[1:], columns=unique_columns)
                                except Exception as e:
                                    st.info(f"PDF table parse error: {e}")
                                    continue
                            else:
                                df_table = pd.DataFrame(table)
                            if not df_table.empty:
                                all_tables.append(df_table)
                    if all_tables:
                        def get_label_amount_table(df):
                            cols = [c.lower() for c in df.columns]
                            label_col = None
        if file_format == 'csv':
            try:
                df = pd.read_csv(io.BytesIO(blob_data))
                st.success(f"Successfully loaded CSV file from blob storage!")
                st.dataframe(df)
                csv_data = df.to_csv(index=False).encode('utf-8')
                json_data = df.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv_data,
                    file_name="data.csv",
                    mime="text/csv"
                )
                st.download_button(
                    label="Download as JSON",
                    data=json_data,
                    file_name="data.json",
                    mime="application/json"
                )
                return df
            except Exception as e:
                st.error(f"CSV read error: {e}")
                return None
        elif file_format == 'excel' or file_format == 'xlsx':
            try:
                excel_file = pd.ExcelFile(io.BytesIO(blob_data))
                all_sheets = []
                for sheet_name in excel_file.sheet_names:
                    df = excel_file.parse(sheet_name)
                    st.write(f"Sheet: {sheet_name}")
                    st.dataframe(df)
                    # Visualization: Bar chart for numeric columns
                    try:
                        numeric_cols = df.select_dtypes(include='number').columns
                        if len(numeric_cols) > 0:
                            st.bar_chart(df[numeric_cols])
                    except Exception as e:
                        st.info(f"Visualization error: {e}")
                    all_sheets.append(df)
                st.success(f"Successfully loaded Excel file from blob storage!")
                if all_sheets:
                    df_all = pd.concat(all_sheets, ignore_index=True)
                    csv_data = df_all.to_csv(index=False).encode('utf-8')
                    json_data = df_all.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
                    st.download_button(
                        label="Download as CSV",
                        data=csv_data,
                        file_name="excel_data.csv",
                        mime="text/csv"
                    )
                    st.download_button(
                        label="Download as JSON",
                        data=json_data,
                        file_name="excel_data.json",
                        mime="application/json"
                    )
                return None
            except Exception as e:
                st.error(f"Excel read error: {e}")
                return None
        elif file_format == 'json':
            try:
                df = pd.read_json(io.BytesIO(blob_data))
                st.success(f"Successfully loaded JSON file from blob storage!")
                st.dataframe(df)
                return df
            except Exception as e:
                st.error(f"JSON read error: {e}")
                return None
        # Try OCR if file is image or fallback for other formats
        if file_format in ['png', 'jpg', 'jpeg', 'bmp', 'tiff'] or selected_path['blob_name'].lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file_format) as tmp_img:
                tmp_img.write(blob_data)
                tmp_img.flush()
                image = Image.open(tmp_img.name)
                ocr_text = pytesseract.image_to_string(image, lang=ocr_lang)
        else:
            # Try to open as image anyway
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
                    tmp_img.write(blob_data)
                    tmp_img.flush()
                    image = Image.open(tmp_img.name)
                    ocr_text = pytesseract.image_to_string(image, lang=ocr_lang)
            except Exception:
                ocr_text = None
        if ocr_text:
            # For non-PDF files, try to extract all items/services and amounts
            summary_pattern = r"(?i)(total|subtotal|budget|[A-Za-z0-9 \-]+)\s*[:\-]?\s*\$?([\d,]+(?:\.\d{2})?)"
            summary_matches = re.findall(summary_pattern, ocr_text)
            table_rows = []
            label_count = {}
            subtotal_row = None
            total_row = None
            address_keywords = ["pin", "house", "street", "road", "avenue", "block", "no", "number", "zip", "postal", "address"]
            for label, amount in summary_matches:
                label_clean = label.strip()
                if label_clean.isdigit():
                    continue
                # Ignore amounts that are only punctuation/symbols
                if all(c in ",.:-_()[]{}|/\\'\"!@#$%^&*" for c in amount.strip()):
                    continue
                label_key = label_clean.lower()
                if any(addr in label_key for addr in address_keywords):
                    continue
                if label_key in label_count:
                    label_count[label_key] += 1
                    label_display = f"{label_clean}_x{label_count[label_key]}"
                else:
                    label_count[label_key] = 1
                    label_display = label_clean
                if label_key in ["subtotal"]:
                    subtotal_row = {"Label": "Subtotal", "Amount": amount}
                elif label_key in ["total", "amount", "total amount", "grand total"]:
                    total_row = {"Label": "Total", "Amount": amount}
                else:
                    table_rows.append({"Label": label_display, "Amount": amount})
            seen = set()
            unique_rows = []
            for row in table_rows:
                key = (row["Label"].lower(), row["Amount"])
                if key not in seen:
                    unique_rows.append(row)
                    seen.add(key)
            if subtotal_row:
                unique_rows.append(subtotal_row)
            if total_row:
                unique_rows.append(total_row)
            if unique_rows:
                df = pd.DataFrame(unique_rows)
                st.success("Extracted items/services and amounts from file!")
                st.dataframe(df)
                if total_row:
                    st.markdown(f"**Total Amount:** {total_row['Amount']}")
                return df
            else:
                st.warning("No items/services or amounts found in file.")
                possible_labels = ["Item/Service", "Subtotal", "Total"]
                df = pd.DataFrame({"Label": possible_labels, "Amount": ["-"]*len(possible_labels)})
                st.dataframe(df)
                return df
        # Fallback to original logic
        if file_format == 'csv':
            df = pd.read_csv(io.BytesIO(blob_data))
            st.success(f"Successfully loaded CSV file from blob storage!")
            st.dataframe(df)
            # Visualization: Bar chart for numeric columns
            try:
                numeric_cols = df.select_dtypes(include='number').columns
                if len(numeric_cols) > 0:
                    st.bar_chart(df[numeric_cols])
            except Exception as e:
                st.info(f"Visualization error: {e}")
            csv_data = df.to_csv(index=False).encode('utf-8')
            json_data = df.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
            st.download_button(
                label="Download as CSV",
                data=csv_data,
                file_name="data.csv",
                mime="text/csv"
            )
            st.download_button(
                label="Download as JSON",
                data=json_data,
                file_name="data.json",
                mime="application/json"
            )
            return df
        elif file_format == 'excel' or file_format == 'xlsx':
            excel_file = pd.ExcelFile(io.BytesIO(blob_data))
            all_sheets = []
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name)
                st.write(f"Sheet: {sheet_name}")
                st.dataframe(df)
                # Visualization: Bar chart for numeric columns
                try:
                    numeric_cols = df.select_dtypes(include='number').columns
                    if len(numeric_cols) > 0:
                        st.bar_chart(df[numeric_cols])
                except Exception as e:
                    st.info(f"Visualization error: {e}")
                all_sheets.append(df)
            st.success(f"Successfully loaded Excel file from blob storage!")
            if all_sheets:
                df_all = pd.concat(all_sheets, ignore_index=True)
                csv_data = df_all.to_csv(index=False).encode('utf-8')
                json_data = df_all.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv_data,
                    file_name="excel_data.csv",
                    mime="text/csv"
                )
                st.download_button(
                    label="Download as JSON",
                    data=json_data,
                    file_name="excel_data.json",
                    mime="application/json"
                )
            return None
        elif file_format == 'json':
            df = pd.read_json(io.BytesIO(blob_data))
            st.success(f"Successfully loaded JSON file from blob storage!")
            st.dataframe(df)
            return df
        else:
            st.info("File format not recognized for tabular display. Downloading raw file.")
            # Show download button for raw file
            file_name = selected_path.get('blob_name', 'raw_file')
            st.download_button(
                label=f"Download Raw File ({file_name})",
                data=blob_data,
                file_name=file_name,
                mime="application/octet-stream"
            )
            return None
    except Exception as e:
        st.error(f"Error reading from blob storage: {e}")
        return None




st.set_page_config(layout="centered", page_title="Blob Data Viewer")


st.title("Azure Blob Storage File Reader")


# --- Error Logging ---
if 'error_log' not in st.session_state:
    st.session_state['error_log'] = []
def log_error(msg):
    st.session_state['error_log'].append(msg)



st.header("1. Azure Blob Storage Connection")
# Hide technical details for a cleaner UI
# st.write(f"**Storage Account Name:** {account_name}")
# st.write(f"**Blob Endpoint:** {blob_endpoint}")


# Use default key from .env if present, else prompt for it
if default_key:
    account_key = default_key
    # st.write("Using default key from .env file.")  # Hide technical info
else:
    account_key = st.text_input("Account Key (from Azure Portal)", type="password")


# Use container name from .env or fallback

# --- Incorporate check_blob.py logic for blob listing ---
from azure.storage.blob import BlobServiceClient

# Use container name from .env or fallback
container_name = os.getenv("AZURE_BLOB_CONTAINER", default_container)

# Build connection string dynamically
connection_string = os.getenv(
    "AZURE_BLOB_CONNECTION_STRING",
    f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
)

blob_name = None
files = []
if connection_string and container_name:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        # Hide blob listing status for clean UI
        for blob in container_client.list_blobs():
            name = blob.name
            # Only include files in the root (no '/')
            if '/' not in name:
                files.append(name)
        if files:
            blob_name = st.selectbox("Select a file", sorted(files))
        else:
            st.warning("No files found in the root of the container.")
    except Exception as e:
        st.error("Unable to access Azure Blob Storage. Please check your credentials or try again later.")
else:
    st.warning("Unable to access blob storage. Please check your credentials.")


# Infer file format from file extension
file_format = "other"
if blob_name:
    if blob_name.lower().endswith(".csv"):
        file_format = "csv"
    elif blob_name.lower().endswith(".xlsx") or blob_name.lower().endswith(".xls"):
        file_format = "excel"
    elif blob_name.lower().endswith(".json"):
        file_format = "json"
    elif blob_name.lower().endswith(".pdf"):
        file_format = "pdf"

selected_path_value = {
    'connection_string': connection_string,
    'container_name': container_name,
    'blob_name': blob_name,
    'file_format': file_format
}





# --- OCR Language Selection ---
st.sidebar.write("## OCR Language")
ocr_lang = st.sidebar.text_input("Tesseract language code (e.g. 'eng', 'deu', 'fra')", value="eng", help="See https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html for codes.")

# --- File Upload Option ---
st.subheader("Or Upload a Local File")
uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls", "json", "pdf", "png", "jpg", "jpeg", "bmp", "tiff"], help="Accessible file uploader")

def handle_uploaded_file(uploaded_file):
    file_name = uploaded_file.name
    file_format = "other"
    if file_name.lower().endswith(".csv"):
        file_format = "csv"
    elif file_name.lower().endswith(".xlsx") or file_name.lower().endswith(".xls"):
        file_format = "excel"
    elif file_name.lower().endswith(".json"):
        file_format = "json"
    elif file_name.lower().endswith(".pdf"):
        file_format = "pdf"
    try:
        if file_format == 'csv':
            df = pd.read_csv(uploaded_file)
            st.dataframe(df)
            try:
                numeric_cols = df.select_dtypes(include='number').columns
                if len(numeric_cols) > 0:
                    st.bar_chart(df[numeric_cols])
            except Exception as e:
                st.info(f"Visualization error: {e}")
            csv_data = df.to_csv(index=False).encode('utf-8')
            json_data = df.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
            st.download_button("Download as CSV", csv_data, file_name="data.csv", mime="text/csv")
            st.download_button("Download as JSON", json_data, file_name="data.json", mime="application/json")
        elif file_format == 'excel':
            excel_file = pd.ExcelFile(uploaded_file)
            sheet = st.selectbox("Select sheet", excel_file.sheet_names)
            df = excel_file.parse(sheet)
            st.dataframe(df)
            try:
                numeric_cols = df.select_dtypes(include='number').columns
                if len(numeric_cols) > 0:
                    st.bar_chart(df[numeric_cols])
            except Exception as e:
                st.info(f"Visualization error: {e}")
            csv_data = df.to_csv(index=False).encode('utf-8')
            json_data = df.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
            st.download_button("Download as CSV", csv_data, file_name="excel_data.csv", mime="text/csv")
            st.download_button("Download as JSON", json_data, file_name="excel_data.json", mime="application/json")
        elif file_format == 'json':
            df = pd.read_json(uploaded_file)
            st.dataframe(df)
        elif file_format == 'pdf':
            import pdfplumber
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                tmp_pdf.write(uploaded_file.read())
                tmp_pdf.flush()
                try:
                    with pdfplumber.open(tmp_pdf.name) as pdf:
                        all_tables = []
                        for page_num, page in enumerate(pdf.pages):
                            tables = page.extract_tables()
                            for table in tables:
                                if len(table) > 1:
                                    df = pd.DataFrame(table[1:], columns=table[0])
                                    st.write(f"Page {page_num+1} Table:")
                                    st.dataframe(df)
                                    all_tables.append(df)
                        if not all_tables:
                            st.info("No tables found in PDF. Preview not available.")
                except Exception as e:
                    st.error(f"PDF preview error: {e}")
                finally:
                    os.unlink(tmp_pdf.name)
        else:
            st.info("Preview not supported for this file type.")
    except Exception as e:
        log_error(f"Upload error: {e}")
        st.error(f"Error reading uploaded file: {e}")

if uploaded_file:
    handle_uploaded_file(uploaded_file)


if blob_name and not uploaded_file:
    if 'is_running' not in st.session_state:
        st.session_state['is_running'] = False
    if 'start_time' not in st.session_state:
        st.session_state['start_time'] = None
    run_btn_label = "CANCEL" if st.session_state['is_running'] else "RUN"
    col1, col2 = st.columns([1,2])
    with col1:
        run_btn = st.button(run_btn_label, help="Activate to process the selected file" if not st.session_state['is_running'] else "Cancel the running process")
    with col2:
        if st.session_state['is_running']:
            import datetime
            # For demonstration, assume ETA is 30 seconds minus elapsed
            if st.session_state['start_time'] is None:
                st.session_state['start_time'] = datetime.datetime.now()
            elapsed = (datetime.datetime.now() - st.session_state['start_time']).total_seconds()
            eta = max(0, 30 - int(elapsed))
            st.info(f"ETA: {eta} seconds")
        else:
            st.session_state['start_time'] = None
    if run_btn:
        if not st.session_state['is_running']:
            st.session_state['is_running'] = True
            st.session_state['start_time'] = None
        else:
            st.session_state['is_running'] = False
            st.session_state['start_time'] = None
            st.warning("Process cancelled by user.")
    if st.session_state['is_running']:
        selected_path_value = {
            'connection_string': connection_string,
            'container_name': container_name,
            'blob_name': blob_name,
            'file_format': file_format
        }
        try:
            # Accessibility: Announce processing
            st.markdown('<div aria-live="polite" style="position:absolute;left:-10000px;top:auto;width:1px;height:1px;overflow:hidden;">Processing file...</div>', unsafe_allow_html=True)
            df = run_connection_and_show_data(selected_path_value, ocr_lang=ocr_lang)
            # --- Sheet Selection for Excel ---
            if file_format in ["excel", "xlsx"] and df is not None:
                st.write("Select sheet to view:")
                # Already handled in run_connection_and_show_data if needed
            # --- Pagination and Filtering ---
            if isinstance(df, pd.DataFrame) and len(df) > 0:
                st.write("Filter/Search Table:")
                filtered_df = dataframe_explorer(df, case=False)
                st.dataframe(filtered_df)
                st.write("Pagination:")
                page_size = st.number_input("Rows per page", min_value=5, max_value=100, value=20)
                total_pages = (len(filtered_df) - 1) // page_size + 1
                page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
                start = (page - 1) * page_size
                end = start + page_size
                st.dataframe(filtered_df.iloc[start:end])
            st.session_state['is_running'] = False
            st.session_state['start_time'] = None
        except Exception as e:
            log_error(f"Blob error: {e}")
            st.error(f"Error: {e}")
            st.session_state['is_running'] = False
            st.session_state['start_time'] = None

# --- Async/Performance Note ---
st.sidebar.info("For very large files, async/background processing is recommended. Streamlit currently processes synchronously, but you can use tools like Streamlit Community Cloud jobs or external APIs for heavy workloads.")

# --- Error Log Download ---
if st.sidebar.button("Download Error Log"):
    log_content = "\n".join(st.session_state['error_log'])
    st.sidebar.download_button("Download Error Log", log_content, file_name="error_log.txt")

# --- User Feedback ---
st.sidebar.write("## Feedback")
feedback = st.sidebar.radio("Was the extraction correct?", ("👍 Yes", "👎 No"))
if feedback:
    st.sidebar.success("Thank you for your feedback!")

# --- Help/Docs Link ---
st.sidebar.markdown("[Help/Documentation](https://github.com/Unigalactix/ocr_to_table#readme)")

st.sidebar.header("About")
st.sidebar.info("This is a simple Streamlit application demonstrating path selection and data display.")

st.sidebar.header("Instructions")
st.sidebar.write("1. Select a storage path from the dropdown.")
st.sidebar.write("2. Click the 'RUN' button to simulate connecting and displaying data.")