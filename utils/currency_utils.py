"""
Currency and Budget Detection Utilities
Contains patterns and functions for identifying budget-related content
"""
import re


# Enhanced currency patterns for detecting monetary values
CURRENCY_PATTERNS = [
    r'[\$€£¥₹]\s*[\d,]+\.?\d*',  # Currency symbols before numbers
    r'[\d,]+\.?\d*\s*[\$€£¥₹]',  # Currency symbols after numbers
    r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b',  # General number patterns
    r'(?:USD|EUR|GBP|INR|AUD|CAD)\s*[\d,]+\.?\d*',  # Currency codes before
    r'[\d,]+\.?\d*\s*(?:USD|EUR|GBP|INR|AUD|CAD)',  # Currency codes after
]

# Keywords that indicate budget/financial content
BUDGET_KEYWORDS = [
    'amount', 'budget', 'cost', 'price', 'total', 'expense', 'payment',
    'fee', 'charge', 'rate', 'value', 'sum', 'balance', 'due', 'revenue',
    'income', 'expenditure', 'allocation', 'fund', 'capital', 'investment',
    'profit', 'loss', 'tax', 'discount', 'refund', 'salary', 'wage'
]

# Currency symbols and codes
CURRENCY_SYMBOLS = ['$', '€', '£', '¥', '₹', '₽', '¢', '₩', '₪', '₦']
CURRENCY_CODES = ['USD', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'JPY', 'CNY', 'RUB']


def contains_currency(text):
    """
    Check if text contains currency patterns.
    
    Args:
        text (str): Text to check
        
    Returns:
        bool: True if currency pattern found
    """
    if not isinstance(text, str):
        text = str(text)
    
    text = text.strip().lower()
    
    # Check for currency patterns
    for pattern in CURRENCY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def contains_budget_keywords(text):
    """
    Check if text contains budget-related keywords.
    
    Args:
        text (str): Text to check
        
    Returns:
        bool: True if budget keywords found
    """
    if not isinstance(text, str):
        text = str(text)
    
    text = text.strip().lower()
    
    return any(keyword in text for keyword in BUDGET_KEYWORDS)


def is_budget_related_content(text):
    """
    Comprehensive check for budget-related content.
    
    Args:
        text (str): Text to check
        
    Returns:
        bool: True if content appears budget-related
    """
    return contains_currency(text) or contains_budget_keywords(text)


def extract_currency_amounts(text):
    """
    Extract all currency amounts from text.
    
    Args:
        text (str): Text to extract from
        
    Returns:
        list: List of found currency amounts
    """
    if not isinstance(text, str):
        text = str(text)
    
    amounts = []
    for pattern in CURRENCY_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        amounts.extend(matches)
    
    return amounts


def is_table_budget_related(dataframe):
    """
    Check if a pandas DataFrame contains budget-related information.
    
    Args:
        dataframe: pandas DataFrame to check
        
    Returns:
        bool: True if table appears budget-related
    """
    # Check column headers
    for col in dataframe.columns:
        if contains_budget_keywords(str(col)):
            return True
    
    # Check cell contents (sample first few rows for performance)
    sample_size = min(10, len(dataframe))
    for _, row in dataframe.head(sample_size).iterrows():
        for cell in row:
            if cell and is_budget_related_content(str(cell)):
                return True
    
    return False
