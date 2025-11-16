"""
File Utilities for Oracle FBDI Integration

Provides utilities for:
- Converting Excel templates to CSV files
- Creating ZIP archives for FBDI upload
- File validation and management
"""

import zipfile
from pathlib import Path
from typing import List
import pandas as pd


def excel_to_csv_and_zip(excel_path: str, zip_path: str) -> str:
    """
    Convert Excel sheets to CSV files and package them in a ZIP archive.

    Args:
        excel_path: Path to the Excel file (.xlsx, .xlsm, .xls)
        zip_path: Path for the output ZIP file

    Returns:
        Path to the created ZIP file

    Raises:
        FileNotFoundError: If Excel file doesn't exist
        ValueError: If file is not a valid Excel file
    """
    excel_file = Path(excel_path)

    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    if excel_file.suffix.lower() not in ['.xlsx', '.xlsm', '.xls']:
        raise ValueError(f"File is not an Excel file: {excel_path}")

    zip_dir = Path(zip_path).parent
    print(f"ZIP will be saved to: {zip_path}")
    print(f"CSV files will be saved to: {zip_dir}")

    xl = pd.ExcelFile(excel_path)
    print(f"Found sheets: {xl.sheet_names}")

    csv_files = []

    for sheet_name in xl.sheet_names:
        if 'instruction' in sheet_name.lower():
            print(f"Skipping instruction sheet: {sheet_name}")
            continue

        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

        # Special handling for GL_INTERFACE / XCC_BUDGET_INTERFACE
        if 'GL_INTERFACE' in sheet_name or 'XCC_BUDGET_INTERFACE' in sheet_name:
            headers = [
                str(df.iloc[3, i]) if pd.notna(df.iloc[3, i]) else f'Col_{i}'
                for i in range(len(df.columns))
            ]
            df = df.iloc[4:].copy()
            df.columns = headers[:len(df.columns)]
            df = df.dropna(how='all')

        else:
            # Detect header row for other sheets
            max_non_null = 0
            header_row = -1
            for i in range(min(10, len(df))):
                non_null_count = df.iloc[i].notna().sum()
                if non_null_count > max_non_null:
                    max_non_null = non_null_count
                    header_row = i
            if header_row >= 0:
                df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
            df = df.dropna(axis=0, how='all').dropna(axis=1, how='all')

        if df.empty:
            print(f"Skipping empty sheet: {sheet_name}")
            continue

        # Determine CSV filename
        clean_name = sheet_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        if 'GL_INTERFACE' in sheet_name:
            csv_filename = zip_dir / "GL_INTERFACE.csv"
        elif 'XCC_BUDGET_INTERFACE' in sheet_name:
            csv_filename = zip_dir / "XccBudgetInterface.csv"
        else:
            csv_filename = zip_dir / f"{clean_name}.csv"

        df.to_csv(csv_filename, index=False, header=False, encoding='utf-8')
        csv_files.append(csv_filename)
        print(f"Created CSV: {csv_filename} ({len(df)} rows, {len(df.columns)} columns)")

    if not csv_files:
        raise ValueError("No valid sheets to convert to CSV")

    # Create ZIP file
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for f in csv_files:
            zf.write(f, arcname=f.name)
    print(f"ZIP created: {zip_path}")

    return zip_path


def create_zip_from_folder(src_path: str, zip_path: str) -> str:
    """
    Create a ZIP archive from a folder or file.

    Args:
        src_path: Path to source folder or file
        zip_path: Path for the output ZIP file

    Returns:
        Path to the created ZIP file

    Raises:
        FileNotFoundError: If source path doesn't exist
    """
    src = Path(src_path)

    if not src.exists():
        raise FileNotFoundError(f"Path not found: {src_path}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if src.is_file():
            # Check if it's an Excel file
            if src.suffix.lower() in ['.xlsx', '.xlsm', '.xls']:
                print("Detected Excel file, converting to CSV...")
                return excel_to_csv_and_zip(str(src), zip_path)
            else:
                # Single non-Excel file
                zf.write(src, arcname=src.name)
        elif src.is_dir():
            # Directory - add all files recursively
            for p in src.rglob("*"):
                if p.is_file():
                    zf.write(p, arcname=p.relative_to(src))
        else:
            raise ValueError(f"Path is neither a file nor a directory: {src_path}")

    return zip_path


def validate_csv_file(csv_path: str, required_columns: List[str] = None) -> bool:
    """
    Validate a CSV file for FBDI upload.

    Args:
        csv_path: Path to the CSV file
        required_columns: List of required column names (optional)

    Returns:
        True if valid, False otherwise
    """
    try:
        df = pd.read_csv(csv_path, nrows=5)
        
        if df.empty:
            print(f"CSV file is empty: {csv_path}")
            return False
        
        if required_columns:
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                print(f"Missing required columns: {missing_columns}")
                return False
        
        print(f"CSV file validated: {csv_path}")
        return True
        
    except Exception as e:
        print(f"Error validating CSV file: {e}")
        return False


def cleanup_old_files(directory: str, pattern: str = "*", keep_recent: int = 5):
    """
    Clean up old generated files, keeping only the most recent ones.

    Args:
        directory: Directory to clean
        pattern: File pattern to match (e.g., "*.zip", "*.xlsm")
        keep_recent: Number of recent files to keep
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return

    files = sorted(dir_path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if len(files) > keep_recent:
        for file_to_delete in files[keep_recent:]:
            try:
                file_to_delete.unlink()
                print(f"Deleted old file: {file_to_delete}")
            except Exception as e:
                print(f"Error deleting {file_to_delete}: {e}")
