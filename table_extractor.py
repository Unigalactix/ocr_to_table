"""
Table Extraction Engine
Core functionality for extracting tables from documents using Azure Document Intelligence
"""
import io
import pandas as pd
from azure.ai.formrecognizer import DocumentAnalysisClient
from utils.currency_utils import is_table_budget_related
from utils.file_utils import clean_dataframe


class TableExtractor:
    """
    Extracts and processes tables from documents using Azure Document Intelligence.
    """
    
    def __init__(self, document_client):
        """
        Initialize table extractor.
        
        Args:
            document_client: Azure DocumentAnalysisClient instance
        """
        self.client = document_client
    
    def extract_tables_from_document(self, file_bytes, file_name):
        """
        Extract tables from document using Azure Document Intelligence.
        
        Args:
            file_bytes (bytes): Document content as bytes
            file_name (str): Name of the file
            
        Returns:
            list: List of table information dictionaries
        """
        try:
            # Use prebuilt-layout model for table extraction
            poller = self.client.begin_analyze_document("prebuilt-layout", io.BytesIO(file_bytes))
            result = poller.result()
            
            extracted_tables = []
            
            if result.tables:
                for table_idx, table in enumerate(result.tables):
                    # Create a structured table representation
                    max_row = max([cell.row_index for cell in table.cells]) + 1
                    max_col = max([cell.column_index for cell in table.cells]) + 1
                    
                    # Initialize table grid
                    table_grid = [[''] * max_col for _ in range(max_row)]
                    
                    # Fill the grid with cell contents
                    for cell in table.cells:
                        table_grid[cell.row_index][cell.column_index] = cell.content.strip()
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(table_grid)
                    df = clean_dataframe(df)
                    
                    # Check if table contains budget-related information
                    is_budget_related = is_table_budget_related(df)
                    
                    table_info = {
                        'table_id': f'Table_{table_idx + 1}',
                        'row_count': table.row_count,
                        'column_count': table.column_count,
                        'is_budget_related': is_budget_related,
                        'dataframe': df,
                        'raw_data': table_grid
                    }
                    
                    extracted_tables.append(table_info)
            
            return extracted_tables
            
        except Exception as e:
            raise RuntimeError(f"Error extracting tables from document: {e}")
    
    def create_consolidated_table(self, extracted_tables):
        """
        Create a single consolidated table from all extracted tables.
        
        Args:
            extracted_tables (list): List of table information dictionaries
            
        Returns:
            pandas.DataFrame: Consolidated table with metadata
        """
        if not extracted_tables:
            return pd.DataFrame()
        
        consolidated_data = []
        
        for table in extracted_tables:
            df = table['dataframe']
            table_id = table['table_id']
            is_budget = table['is_budget_related']
            
            # Add each row of the table to consolidated data
            for row_idx, row in df.iterrows():
                # Convert row to a dictionary with column names
                row_data = {}
                for col_idx, cell in enumerate(row):
                    col_name = f"Column_{col_idx + 1}"
                    row_data[col_name] = str(cell) if cell else ""
                
                # Add metadata columns
                row_data['Source_Table'] = table_id
                row_data['Budget_Related'] = "Yes" if is_budget else "No"
                row_data['Row_Number'] = row_idx + 1
                
                consolidated_data.append(row_data)
        
        # Create DataFrame with consistent columns
        if consolidated_data:
            df = pd.DataFrame(consolidated_data)
            
            # Reorder columns to put metadata first
            metadata_cols = ['Source_Table', 'Budget_Related', 'Row_Number']
            data_cols = [col for col in df.columns if col not in metadata_cols]
            df = df[metadata_cols + sorted(data_cols)]
            
            return df
        
        return pd.DataFrame()
    
    def filter_budget_tables(self, extracted_tables):
        """
        Filter tables to separate budget-related from other tables.
        
        Args:
            extracted_tables (list): List of table information dictionaries
            
        Returns:
            tuple: (budget_tables, other_tables)
        """
        budget_tables = []
        other_tables = []
        
        for table in extracted_tables:
            if table['is_budget_related']:
                budget_tables.append(table)
            else:
                other_tables.append(table)
        
        return budget_tables, other_tables
