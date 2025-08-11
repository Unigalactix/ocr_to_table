"""
Streamlit UI Components
Handles all user interface elements and interactions
"""
import streamlit as st
import pandas as pd
from utils.file_utils import is_excel_file


class UIHandler:
    """
    Manages all Streamlit UI components and user interactions.
    """
    
    def __init__(self):
        """Initialize UI handler."""
        self.setup_page_config()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(page_title="Budget Table Extractor", layout="wide")
        st.title("Budget Table Extractor")
    
    def render_file_source_selector(self):
        """
        Render file source selection (Azure Blob or Local Upload).
        
        Returns:
            str: Selected file source option
        """
        return st.sidebar.radio("File source:", ["Azure Blob", "Local Upload"])
    
    def render_blob_file_selector(self, blob_files):
        """
        Render blob file selection dropdown.
        
        Args:
            blob_files (list): List of available blob files
            
        Returns:
            str: Selected blob file name
        """
        if blob_files:
            return st.sidebar.selectbox("Select file:", blob_files)
        else:
            st.sidebar.info("No files found in blob storage")
            return None
    
    def render_file_uploader(self):
        """
        Render local file upload widget.
        
        Returns:
            UploadedFile: Streamlit uploaded file object
        """
        return st.sidebar.file_uploader(
            "Upload file", 
            type=['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'csv', 'xlsx', 'xls'],
            help="PDF/Images: Table extraction with budget focus | CSV/Excel: Direct processing"
        )
    
    def render_extract_button(self, current_file):
        """
        Render extract tables button.
        
        Args:
            current_file (str): Current file name
            
        Returns:
            bool: True if button was clicked
        """
        return current_file and st.sidebar.button("Extract Tables")
    
    def show_processing_info(self, file_name, file_type):
        """
        Show processing information to user.
        
        Args:
            file_name (str): Name of the file being processed
            file_type (str): Type of processing (CSV/Excel or Document)
        """
        st.info(f"Processing: {file_name}")
        
        if file_type == "csv_excel":
            st.info("CSV/Excel file processed directly (Table extraction skipped)")
        elif file_type == "document":
            st.info("Extracting tables from document using Azure Document Intelligence...")
    
    def display_consolidated_table(self, consolidated_table, current_file):
        """
        Display the consolidated table with download options.
        
        Args:
            consolidated_table (pandas.DataFrame): Consolidated table data
            current_file (str): Current file name for download naming
        """
        if consolidated_table is not None and not consolidated_table.empty:
            st.subheader("Consolidated Table Data")
            st.dataframe(consolidated_table, use_container_width=True)
            
            # Show summary information
            budget_count = len(consolidated_table[consolidated_table['Budget_Related'] == 'Yes'])
            total_count = len(consolidated_table)
            st.info(f"Total rows: {total_count} | Budget-related rows: {budget_count}")
            
            # Download consolidated table as JSON
            json_data = consolidated_table.to_json(orient='records', force_ascii=False, indent=2)
            st.download_button(
                "Download Consolidated Table JSON",
                json_data,
                f"{current_file}_consolidated_table.json",
                "application/json"
            )
            return True
        return False
    
    def display_excel_csv_sheets(self, sheets, current_file, file_name):
        """
        Display Excel/CSV sheet data.
        
        Args:
            sheets (dict): Dictionary of sheet data
            current_file (str): Current file name
            file_name (str): Original file name
        """
        if sheets:
            st.subheader("Excel/CSV Data")
            if is_excel_file(file_name):
                st.info("Excel format: A, B, C columns; 1, 2, 3 rows")
            
            for sheet_name, sheet_df in sheets.items():
                with st.expander(f"{sheet_name} ({len(sheet_df)} rows, {len(sheet_df.columns)} cols)"):
                    st.dataframe(sheet_df.fillna(''), use_container_width=True)
                    json_data = sheet_df.to_json(orient='records', force_ascii=False, indent=2)
                    st.download_button(
                        f"Download {sheet_name} JSON",
                        json_data,
                        f"{current_file}_{sheet_name}.json",
                        "application/json",
                        key=f"sheet_{sheet_name}"
                    )
            return True
        return False
    
    def show_no_tables_message(self):
        """Show message when no tables are found."""
        st.info("No tables found in the document. The document may not contain structured tabular data.")
    
    def show_error(self, message):
        """
        Show error message to user.
        
        Args:
            message (str): Error message to display
        """
        st.error(message)
    
    def show_warning(self, message):
        """
        Show warning message to user.
        
        Args:
            message (str): Warning message to display
        """
        st.warning(message)
