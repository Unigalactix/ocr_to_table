"""
File Processing Utilities
Handles reading and processing of different file formats
"""
import io
import pandas as pd


def is_csv_or_excel_file(filename):
    """Check if file is CSV or Excel format."""
    return filename.lower().endswith(('.csv', '.xlsx', '.xls'))


def is_document_or_image_file(filename):
    """Check if file is a document or image format."""
    return filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'))


def is_excel_file(filename):
    """Check if file is Excel format."""
    return filename.lower().endswith(('.xlsx', '.xls'))


def generate_excel_column_names(num_columns):
    """
    Generate Excel-style column names (A, B, C, ..., AA, AB, etc.)
    
    Args:
        num_columns (int): Number of columns needed
        
    Returns:
        list: List of Excel-style column names
    """
    columns = []
    for i in range(num_columns):
        column = ''
        temp = i
        while True:
            column = chr(65 + (temp % 26)) + column
            temp //= 26
            if temp == 0:
                break
            temp -= 1
        columns.append(column)
    return columns


def read_csv_or_excel_file(file_bytes, file_name):
    """
    Read CSV or Excel file and return processed data.
    
    Args:
        file_bytes (bytes): File content as bytes
        file_name (str): Name of the file
        
    Returns:
        tuple: (None, None, None, sheets_dict) for compatibility
    """
    try:
        file_obj = io.BytesIO(file_bytes)
        sheets = {}
        
        if is_excel_file(file_name):
            # Handle Excel files with multiple sheets
            excel_file = pd.ExcelFile(file_obj)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, dtype=str)
                excel_columns = generate_excel_column_names(len(df.columns))
                df.columns = excel_columns
                df.index = range(1, len(df) + 1)
                sheets[sheet_name] = df
        else:
            # Handle CSV files
            df = pd.read_csv(file_obj, header=None, dtype=str)
            excel_columns = generate_excel_column_names(len(df.columns))
            df.columns = excel_columns
            df.index = range(1, len(df) + 1)
            sheets['Sheet1'] = df
        
        return None, None, None, sheets
    except Exception as e:
        raise RuntimeError(f"Error reading file '{file_name}': {e}")


def clean_dataframe(df):
    """
    Clean a pandas DataFrame by removing empty rows and handling null values.
    
    Args:
        df (pandas.DataFrame): DataFrame to clean
        
    Returns:
        pandas.DataFrame: Cleaned DataFrame
    """
    # Remove completely empty rows
    df = df.dropna(how='all')
    
    # Remove rows where all values are empty strings
    df = df[~df.apply(lambda row: row.astype(str).str.strip().eq('').all(), axis=1)]
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df
