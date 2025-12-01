"""
Base64 to Excel Converter Utility

This script converts base64-encoded Excel data to an Excel file.
Can be used as a standalone script or imported as a module.
"""

import base64
import io
import pandas as pd
from pathlib import Path


def base64_to_excel(base64_string: str, output_path: str = None) -> pd.DataFrame:
    """
    Convert a base64-encoded Excel file to a DataFrame and optionally save to file.
    
    Args:
        base64_string: Base64-encoded Excel file content
        output_path: Optional path to save the Excel file (e.g., 'output.xlsx')
    
    Returns:
        pd.DataFrame: The Excel data as a pandas DataFrame
    
    Example:
        >>> df = base64_to_excel(base64_string, 'output.xlsx')
        >>> print(df.head())
    """
    # Remove any whitespace or newlines from base64 string
    base64_string = base64_string.strip().replace('\n', '').replace('\r', '')
    
    # Decode base64 to bytes
    excel_bytes = base64.b64decode(base64_string)
    
    # Read Excel from bytes
    df = pd.read_excel(io.BytesIO(excel_bytes))
    
    # Optionally save to file
    if output_path:
        # Create output directory if it doesn't exist
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save based on file extension
        if output_path.endswith('.xlsx'):
            df.to_excel(output_path, index=False)
        elif output_path.endswith('.csv'):
            df.to_csv(output_path, index=False)
        else:
            df.to_excel(output_path + '.xlsx', index=False)
        
        print(f"Excel file saved to: {output_path}")
    
    return df


def base64_to_excel_bytes(base64_string: str) -> bytes:
    """
    Convert base64 string to Excel file bytes (without saving to disk).
    
    Args:
        base64_string: Base64-encoded Excel file content
    
    Returns:
        bytes: Raw Excel file bytes
    """
    base64_string = base64_string.strip().replace('\n', '').replace('\r', '')
    return base64.b64decode(base64_string)


def excel_to_base64(file_path: str) -> str:
    """
    Convert an Excel file to base64 string.
    
    Args:
        file_path: Path to the Excel file
    
    Returns:
        str: Base64-encoded string of the Excel file
    """
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    
    return base64.b64encode(file_bytes).decode('utf-8')


def dataframe_to_base64(df: pd.DataFrame) -> str:
    """
    Convert a pandas DataFrame to base64-encoded Excel string.
    
    Args:
        df: pandas DataFrame to convert
    
    Returns:
        str: Base64-encoded Excel file
    """
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return base64.b64encode(output.read()).decode('utf-8')


if __name__ == "__main__":
    import sys
    
    # Example usage from command line
    if len(sys.argv) >= 2:
        # If a file path is provided, read base64 from file
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) >= 3 else 'output.xlsx'
        
        with open(input_file, 'r') as f:
            base64_content = f.read()
        
        df = base64_to_excel(base64_content, output_file)
        print(f"Converted {input_file} to {output_file}")
        print(f"DataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
    else:
        # Interactive mode - paste base64 string
        print("Base64 to Excel Converter")
        print("=" * 40)
        print("Enter base64 string (press Enter twice to finish):")
        
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        
        if lines:
            base64_content = "".join(lines)
            df = base64_to_excel(base64_content, "output.xlsx")
            print(f"\nConverted successfully!")
            print(f"DataFrame shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print(f"\nPreview (first 5 rows):")
            print(df.head())
        else:
            print("No input provided.")
