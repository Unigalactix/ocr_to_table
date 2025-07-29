
import streamlit as st
import pandas as pd
import time # For simulating connection delay
import json
import os



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


def run_connection_and_show_data(selected_path):
    """
    Connects to Azure Blob Storage and reads a file of any format.
    """
    from azure.storage.blob import BlobServiceClient
    import io
    st.write(f"Attempting to connect to: **{selected_path}**...")
    time.sleep(1)
    st.info("Connecting to Azure Blob Storage...")
    try:
        blob_service_client = BlobServiceClient.from_connection_string(selected_path['connection_string'])
        blob_client = blob_service_client.get_blob_client(container=selected_path['container_name'], blob=selected_path['blob_name'])
        blob_data = blob_client.download_blob().readall()
        file_format = selected_path['file_format'].lower()
        # OCR logic for any file format
        import pytesseract
        from PIL import Image
        import tempfile
        import pdfplumber
        import re
        ocr_text = None
        # PDF OCR logic
        if file_format == 'pdf' or selected_path['blob_name'].lower().endswith('.pdf'):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                tmp_pdf.write(blob_data)
                tmp_pdf.flush()
                with pdfplumber.open(tmp_pdf.name) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                    ocr_text = text
            # Extract label-value pairs for summary amounts
            summary_pattern = r"(?i)(total|subtotal|budget|[A-Za-z0-9 \-]+)\s*[:\-]?\s*\$?([\d,]+(?:\.\d{2})?)"
            summary_matches = re.findall(summary_pattern, ocr_text)
            # Build single table with all found items/services and summary labels
            table_rows = []
            label_count = {}
            subtotal_row = None
            total_row = None
            address_keywords = ["pin", "house", "street", "road", "avenue", "block", "no", "number", "zip", "postal", "address"]
            city_names = [
                "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia", "san antonio", "san diego", "dallas", "san jose", "austin", "jacksonville", "fort worth", "columbus", "charlotte", "san francisco", "indianapolis", "seattle", "denver", "washington", "boston", "el paso", "nashville", "detroit", "oklahoma city", "portland", "las vegas", "memphis", "louisville", "baltimore", "milwaukee", "albuquerque", "tucson", "fresno", "sacramento", "kansas city", "long beach", "mesa", "atlanta", "colorado springs", "virginia beach", "raleigh", "omaha", "miami", "oakland", "minneapolis", "tulsa", "wichita", "new orleans", "arlington"
            ]
            for label, amount in summary_matches:
                label_clean = label.strip()
                # Ignore labels that are only numbers
                if label_clean.isdigit():
                    continue
                # Ignore labels that are only symbols or punctuation
                if all(c in ",.:-_()[]{}|/\\'\"!@#$%^&*" for c in label_clean):
                    continue
                # Ignore amounts that are only punctuation/symbols
                if all(c in ",.:-_()[]{}|/\\'\"!@#$%^&*" for c in amount.strip()):
                    continue
                # Ignore labels that are only city names (case-insensitive, no description)
                label_key = label_clean.lower()
                if any(addr in label_key for addr in address_keywords):
                    continue
                if label_key in city_names:
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
            # Remove duplicates by label and amount
            seen = set()
            unique_rows = []
            for row in table_rows:
                key = (row["Label"].lower(), row["Amount"])
                if key not in seen:
                    unique_rows.append(row)
                    seen.add(key)
            # Always show subtotal and total at the bottom
            if subtotal_row:
                unique_rows.append(subtotal_row)
            if total_row:
                unique_rows.append(total_row)
            if unique_rows:
                df = pd.DataFrame(unique_rows)
                st.success("Extracted items/services and amounts from PDF!")
                st.dataframe(df)
                # Show total amount summary below table if present
                if total_row:
                    st.markdown(f"**Total Amount:** {total_row['Amount']}")
                return df
            else:
                st.warning("No items/services or amounts found in PDF.")
                possible_labels = ["Item/Service", "Subtotal", "Total"]
                df = pd.DataFrame({"Label": possible_labels, "Amount": ["-"]*len(possible_labels)})
                st.dataframe(df)
                return df
        # Try OCR if file is image or fallback for other formats
        if file_format in ['png', 'jpg', 'jpeg', 'bmp', 'tiff'] or selected_path['blob_name'].lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file_format) as tmp_img:
                tmp_img.write(blob_data)
                tmp_img.flush()
                image = Image.open(tmp_img.name)
                ocr_text = pytesseract.image_to_string(image)
        else:
            # Try to open as image anyway
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
                    tmp_img.write(blob_data)
                    tmp_img.flush()
                    image = Image.open(tmp_img.name)
                    ocr_text = pytesseract.image_to_string(image)
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
            return df
        elif file_format == 'excel' or file_format == 'xlsx':
            df = pd.read_excel(io.BytesIO(blob_data))
            st.success(f"Successfully loaded Excel file from blob storage!")
            return df
        elif file_format == 'json':
            df = pd.read_json(io.BytesIO(blob_data))
            st.success(f"Successfully loaded JSON file from blob storage!")
            return df
        else:
            st.info("File format not recognized for tabular display. Downloading raw file.")
            return blob_data
    except Exception as e:
        st.error(f"Error reading from blob storage: {e}")
        return None


st.set_page_config(layout="centered", page_title="Blob Data Viewer")

st.title("Azure Blob Storage File Reader")

# --- Azure Blob Storage Details ---



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

# --- RUN Button ---

# Show table when a file is selected and RUN is pressed
if blob_name and st.button("RUN"):
    selected_path_value = {
        'connection_string': connection_string,
        'container_name': container_name,
        'blob_name': blob_name,
        'file_format': file_format
    }
    result = run_connection_and_show_data(selected_path_value)
    if isinstance(result, pd.DataFrame):
        st.subheader("Generated Data Table")
        st.dataframe(result)
        # Add download buttons for CSV and JSON
        csv_data = result.to_csv(index=False).encode('utf-8')
        json_data = result.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
        st.download_button(
            label="Download table as CSV",
            data=csv_data,
            file_name="extracted_table.csv",
            mime="text/csv"
        )
        st.download_button(
            label="Download table as JSON",
            data=json_data,
            file_name="extracted_table.json",
            mime="application/json"
        )

st.sidebar.header("About")
st.sidebar.info("This is a simple Streamlit application demonstrating path selection and data display.")

st.sidebar.header("Instructions")
st.sidebar.write("1. Select a storage path from the dropdown.")
st.sidebar.write("2. Click the 'RUN' button to simulate connecting and displaying data.")