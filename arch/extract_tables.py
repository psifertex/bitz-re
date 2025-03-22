#!/usr/bin/env python3
"""
Extract instruction set tables from the unSP Instruction Set Summary PDF
using Camelot and convert to a structured JSON format.

Dependencies:
    - camelot-py
    - opencv-python
    - ghostscript
    - pdf2image
    - pillow
"""

import camelot
import json
import sys
import argparse
import re
from pathlib import Path

def extract_tables(pdf_path, output_path):
    """
    Extract tables from the PDF and convert to JSON format.
    
    Args:
        pdf_path: Path to the unSP Instruction Set Summary PDF
        output_path: Path to save the output JSON file
    """
    print(f"Extracting tables from {pdf_path}...")
    
    # Extract tables from all pages (PDF only has 7 pages total)
    tables = camelot.read_pdf(
        pdf_path, 
        pages='1-7',
        flavor='lattice',  # Use lattice for table with lines
        line_scale=40,     # Adjust based on the PDF's table lines
    )
    
    print(f"Found {len(tables)} tables")
    
    # Initialize data structure for instruction set
    instruction_set = {
        "instruction_set": [],
        "registers": {}
    }
    
    # Process each table
    for i, table in enumerate(tables):
        print(f"Processing table {i+1}...")
        df = table.df
        
        # Save raw CSV for debugging
        df.to_csv(f"{output_path.parent}/table_{i+1}.csv")
        
        # Process the table based on its structure
        # This will need to be customized based on the actual table structure
        if i == 0:  # Assuming first table is main instruction table
            process_instruction_table(df, instruction_set)
        elif "register" in df.iloc[0, 0].lower():  # Register table
            process_register_table(df, instruction_set)
    
    # Save the extracted data to JSON
    with open(output_path, 'w') as f:
        json.dump(instruction_set, f, indent=2)
    
    print(f"Saved instruction set data to {output_path}")
    print(f"Please manually review and correct the JSON data!")


def process_instruction_table(df, instruction_set):
    """
    Process the main instruction table.
    
    This is a placeholder implementation - you'll need to adapt this
    based on the actual structure of the tables in your PDF.
    """
    # Column names might be in the first or second row
    header_row = 0 if "ISA" in df.iloc[0, 0] else 1
    
    # Set column names from header row
    columns = df.iloc[header_row].tolist()
    
    # Process each row as an instruction
    for i in range(header_row + 1, len(df)):
        row = df.iloc[i].tolist()
        
        # Skip empty rows
        if not row[0] or row[0].isspace():
            continue
            
        # Create instruction entry (this is simplified)
        instruction = {
            "name": row[0].strip() if row[0] else "UNKNOWN",
            "syntax": row[1].strip() if len(row) > 1 and row[1] else "",
            "encoding": {
                "opcode": "",  # Extract from binary columns
                "fields": []
            }
        }
        
        # Add the instruction if it looks valid
        if instruction["name"] != "UNKNOWN":
            instruction_set["instruction_set"].append(instruction)


def process_register_table(df, instruction_set):
    """
    Process register mapping tables.
    
    This is a placeholder implementation - you'll need to adapt this
    based on the actual structure of the register tables in your PDF.
    """
    # Example implementation for register tables
    register_type = "unknown"
    register_map = {}
    
    # Try to determine register type
    if df.iloc[0, 0] and "Rs/Rd" in df.iloc[0, 0]:
        register_type = "Rs_Rd"
    elif df.iloc[0, 0] and "Ra/Rb" in df.iloc[0, 0]:
        register_type = "Ra_Rb"
    
    # Process register mappings
    for i in range(1, len(df)):
        if len(df.iloc[i]) >= 2:
            reg_name = df.iloc[i, 0].strip()
            reg_code = df.iloc[i, 1].strip()
            
            if reg_name and reg_code:
                register_map[reg_code] = reg_name
    
    # Add to instruction set if we have data
    if register_map:
        instruction_set["registers"][register_type] = register_map


def main():
    parser = argparse.ArgumentParser(description="Extract unSP instruction set tables from PDF")
    parser.add_argument("pdf_file", help="Path to the unSP Instruction Set Summary PDF")
    parser.add_argument("-o", "--output", default="unsp_instruction_set.json",
                        help="Output JSON file path (default: unsp_instruction_set.json)")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_file)
    output_path = Path(args.output)
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    extract_tables(pdf_path, output_path)


if __name__ == "__main__":
    main()