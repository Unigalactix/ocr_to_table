"""
Main Application Entry Point
Minimal main file that orchestrates all components
"""
import streamlit as st
from config import AzureConfig
from utils.blob_manager import BlobManager
from utils.file_utils import (
    is_csv_or_excel_file, 
    is_document_or_image_file, 
    read_csv_or_excel_file
)
from table_extractor import TableExtractor
from ui_handler import UIHandler


def initialize_services():
    """
    Initialize all required services and configurations.
    
    Returns:
        tuple: (config, blob_manager, table_extractor, ui_handler)
    """
    try:
        config = AzureConfig()
        ui_handler = UIHandler()
        
        # Initialize Document Intelligence client
        document_client = config.get_document_client()
        table_extractor = TableExtractor(document_client)
        
        # Initialize Blob Manager if credentials available
        blob_manager = None
        if config.has_blob_storage():
            blob_manager = BlobManager(
                config.blob_connection_string, 
                config.blob_container
            )
        
        return config, blob_manager, table_extractor, ui_handler
        
    except Exception as e:
        st.error(f"Failed to initialize services: {e}")
        st.stop()


def get_file_data(file_source, blob_manager, uploaded_file, selected_file):
    """
    Get file data based on source (blob or upload).
    
    Args:
        file_source (str): File source type
        blob_manager: Blob manager instance
        uploaded_file: Uploaded file object
        selected_file (str): Selected blob file name
        
    Returns:
        tuple: (file_bytes, file_name)
    """
    if file_source == "Azure Blob" and selected_file and blob_manager:
        file_bytes = blob_manager.download_file(selected_file)
        file_name = selected_file
    elif file_source == "Local Upload" and uploaded_file:
        file_bytes = uploaded_file.read()
        file_name = uploaded_file.name
    else:
        return None, None
    
    return file_bytes, file_name


def process_file(file_bytes, file_name, table_extractor, ui_handler):
    """
    Process file based on its type.
    
    Args:
        file_bytes (bytes): File content
        file_name (str): File name
        table_extractor: Table extractor instance
        ui_handler: UI handler instance
        
    Returns:
        tuple: (consolidated_table, sheets)
    """
    if is_csv_or_excel_file(file_name):
        # Process CSV/Excel files directly
        ui_handler.show_processing_info(file_name, "csv_excel")
        _, _, _, sheets = read_csv_or_excel_file(file_bytes, file_name)
        return None, sheets
        
    elif is_document_or_image_file(file_name):
        # Process documents/images with OCR
        ui_handler.show_processing_info(file_name, "document")
        extracted_tables = table_extractor.extract_tables_from_document(file_bytes, file_name)
        consolidated_table = table_extractor.create_consolidated_table(extracted_tables)
        return consolidated_table, {}
        
    else:
        ui_handler.show_error(f"Unsupported file type: {file_name}")
        st.stop()


def main():
    """Main application function."""
    # Initialize all services
    config, blob_manager, table_extractor, ui_handler = initialize_services()
    
    # Render UI components
    file_source = ui_handler.render_file_source_selector()
    
    # Handle file selection based on source
    selected_file = None
    uploaded_file = None
    
    if file_source == "Azure Blob":
        if blob_manager:
            try:
                blob_files = blob_manager.list_files()
                selected_file = ui_handler.render_blob_file_selector(blob_files)
            except Exception as e:
                ui_handler.show_error(f"Error accessing blob storage: {e}")
        else:
            ui_handler.show_warning("Blob storage not configured. Please check your environment variables.")
    else:
        uploaded_file = ui_handler.render_file_uploader()
    
    # Determine current file
    current_file = selected_file if file_source == "Azure Blob" else (uploaded_file.name if uploaded_file else None)
    
    # Process file when extract button is clicked
    if ui_handler.render_extract_button(current_file):
        try:
            # Get file data
            file_bytes, file_name = get_file_data(file_source, blob_manager, uploaded_file, selected_file)
            
            if not file_bytes:
                ui_handler.show_error("Could not read file.")
                return
            
            # Process the file
            consolidated_table, sheets = process_file(file_bytes, file_name, table_extractor, ui_handler)
            
            # Display results
            displayed_consolidated = ui_handler.display_consolidated_table(consolidated_table, current_file)
            displayed_sheets = ui_handler.display_excel_csv_sheets(sheets, current_file, file_name)
            
            # Show message if no data found
            if not displayed_consolidated and not displayed_sheets:
                ui_handler.show_no_tables_message()
                
        except Exception as e:
            ui_handler.show_error(f"Error processing file: {e}")


if __name__ == "__main__":
    main()
