#!/usr/bin/env python3
"""
unSP Disassembler - A Python-based disassembler for the unSP instruction set

This disassembler parses the binary representation of unSP instructions and
produces their assembly language representation based on the instruction
set summary documentation.
"""

import json
import sys
import struct
import argparse
from typing import Dict, List, Tuple, Optional, Any, Union


class UnSPDisassembler:
    def __init__(self, instruction_set_file: str = "unsp_instruction_set.json"):
        """Initialize the disassembler with the instruction set definition."""
        with open(instruction_set_file, 'r') as f:
            self.instruction_set_data = json.load(f)
        
        self.instructions = self.instruction_set_data["instruction_set"]
        self.registers = self.instruction_set_data["registers"]
        
        # Sort instructions by opcode length (descending) to prioritize longer matches
        self.instructions.sort(key=lambda x: len(x["encoding"]["opcode"]), reverse=True)

    def _extract_bits(self, value: int, start: int, end: int) -> int:
        """Extract a bit field from a value.
        
        Args:
            value: The integer value to extract bits from
            start: The starting bit position (MSB)
            end: The ending bit position (LSB)
            
        Returns:
            The extracted bit field value
        """
        # Handle range specifications like "15:10"
        if isinstance(start, str) and ":" in start:
            parts = start.split(":")
            start = int(parts[0])
            end = int(parts[1])
        
        mask = ((1 << (start - end + 1)) - 1) << end
        return (value & mask) >> end

    def _match_opcode(self, instruction: int) -> Tuple[Optional[Dict], int]:
        """Find the instruction that matches the given opcode.
        
        Args:
            instruction: The instruction word
            
        Returns:
            A tuple containing the matched instruction definition and the number of bits matched
        """
        for instr in self.instructions:
            opcode = instr["encoding"]["opcode"]
            opcode_len = len(opcode)
            instr_opcode = self._extract_bits(instruction, 15, 16 - opcode_len)
            
            # Convert binary string to integer for comparison
            opcode_int = int(opcode, 2)
            
            if instr_opcode == opcode_int:
                return instr, opcode_len
                
        return None, 0

    def _get_register_name(self, reg_type: str, value: int) -> str:
        """Get the register name for a given register type and value.
        
        Args:
            reg_type: The register type (e.g., "Rs_Rd", "Ra_Rb", "Rx_Ry")
            value: The register value
            
        Returns:
            The register name as a string
        """
        value_bin = format(value, '03b')  # Default to 3-bit format
        
        if reg_type == "Ra_Rb":
            value_bin = format(value, '04b')  # 4-bit format for Ra/Rb
            
        if reg_type == "Rs_Rd":
            return self.registers["Rs_Rd"].get(value_bin, f"Unknown({value_bin})")
        elif reg_type == "Ra_Rb":
            return self.registers["Ra_Rb"].get(value_bin, f"Unknown({value_bin})")
        elif reg_type == "Rx_Ry":
            return self.registers["Rx_Ry"].get(value_bin, f"Unknown({value_bin})")
        else:
            return f"R{value}"

    def disassemble_instruction(self, data: bytes, address: int) -> Tuple[str, int]:
        """Disassemble a single instruction.
        
        Args:
            data: The binary data containing the instruction
            address: The current address of the instruction
            
        Returns:
            A tuple containing the disassembled instruction string and the number of bytes consumed
        """
        if len(data) < 2:
            return "Insufficient data", 0
        
        # Read the first word (16 bits)
        instr_word = struct.unpack("<H", data[:2])[0]
        
        # Find the matching instruction
        instr_def, opcode_bits = self._match_opcode(instr_word)
        if not instr_def:
            return f"Unknown instruction: 0x{instr_word:04x}", 2
        
        # Get the instruction name and base syntax
        instr_name = instr_def["name"]
        syntax = instr_def["syntax"]
        
        # Get the field values
        field_values = {}
        second_word_needed = False
        
        # Check if there are fields to extract
        if "fields" in instr_def["encoding"]:
            for field in instr_def["encoding"]["fields"]:
                # Check if this field requires the second word
                if field.get("second_word", False):
                    second_word_needed = True
                    continue
                
                field_name = field["name"]
                
                # Extract bit positions
                if "bits" in field:
                    bit_spec = field["bits"]
                    
                    # Handle range format like "15:10"
                    if ":" in bit_spec:
                        start, end = map(int, bit_spec.split(":"))
                        field_values[field_name] = self._extract_bits(instr_word, start, end)
                    else:
                        # Single bit
                        bit_pos = int(bit_spec)
                        field_values[field_name] = (instr_word >> bit_pos) & 1
                        
                # Special case for field combinations (like in INT_SET)
                if "values" in field and not isinstance(field["values"], dict):
                    # Skip fields that are just containers for value lookups
                    continue
                
                # Handle register fields
                if field.get("register", False):
                    reg_value = field_values[field_name]
                    # Determine register type based on field name
                    if field_name.startswith("Ra") or field_name.startswith("Rb"):
                        reg_type = "Ra_Rb"
                    elif field_name.startswith("Rx") or field_name.startswith("Ry"):
                        reg_type = "Rx_Ry"
                    else:
                        reg_type = "Rs_Rd"
                        
                    field_values[field_name] = self._get_register_name(reg_type, reg_value)
        
        # Handle second word if needed
        bytes_consumed = 2
        if second_word_needed:
            if len(data) < 4:
                return f"Incomplete instruction {instr_name} (needs second word)", 2
                
            second_word = struct.unpack("<H", data[2:4])[0]
            bytes_consumed = 4
            
            # Process fields in the second word
            for field in instr_def["encoding"]["fields"]:
                if field.get("second_word", False):
                    field_name = field["name"]
                    bit_spec = field["bits"]
                    
                    # Handle range format like "15:0"
                    if ":" in bit_spec:
                        start, end = map(int, bit_spec.split(":"))
                        field_values[field_name] = self._extract_bits(second_word, start, end)
                    else:
                        # Single bit
                        bit_pos = int(bit_spec)
                        field_values[field_name] = (second_word >> bit_pos) & 1
        
        # Substitute field values into the syntax
        result = syntax
        
        # Handle special format for opcodes with value mapping
        for field_name, field_value in field_values.items():
            # Look up the field in the instruction definition
            field_def = next((f for f in instr_def["encoding"].get("fields", []) 
                             if f["name"] == field_name), None)
            
            # If the field has value mappings and the value exists in the mapping
            if field_def and "values" in field_def:
                # Convert field_value to binary string with appropriate length
                if isinstance(field_value, int):
                    # Determine the bit width from the field definition
                    if ":" in field_def.get("bits", ""):
                        start, end = map(int, field_def["bits"].split(":"))
                        bit_width = start - end + 1
                    else:
                        bit_width = 1
                        
                    value_str = format(field_value, f'0{bit_width}b')
                    
                    # Look up the string value from the mapping
                    if value_str in field_def["values"]:
                        field_values[field_name] = field_def["values"][value_str]
            
            # For A22, A16, and similar address fields
            if field_name.startswith("A") and "[" in field_name and ":" in field_name:
                # This is part of a multi-part address, don't replace yet
                continue
                
        # Handle special cases for address fields (A22, A16)
        if "A22[21:16]" in field_values and "A22[15:0]" in field_values:
            address_value = (field_values["A22[21:16]"] << 16) | field_values["A22[15:0]"]
            result = result.replace("A22", f"0x{address_value:06x}")
        elif "A16" in field_values:
            address_value = field_values["A16"]
            result = result.replace("A16", f"0x{address_value:04x}")
        
        # Replace remaining placeholders
        for field_name, field_value in field_values.items():
            # Skip already handled special cases
            if field_name in ["A22[21:16]", "A22[15:0]"]:
                continue
                
            # For regular fields, do a simple replacement
            if isinstance(field_value, int):
                if field_name.startswith("IM"):
                    # Immediate values in hex
                    result = result.replace(field_name, f"0x{field_value:x}")
                else:
                    result = result.replace(field_name, str(field_value))
            else:
                result = result.replace(field_name, str(field_value))
        
        # Clean up any remaining placeholders like {D:} when D=0
        result = result.replace("{D:}", "") if field_values.get("D", 0) == 0 else result.replace("{D:}", "D:")
        
        # Format the output with address and raw bytes
        raw_bytes = " ".join([f"{data[i]:02x}" for i in range(bytes_consumed)])
        return f"{instr_name} {result}", bytes_consumed

    def disassemble_file(self, input_file: str, output_file: str = None, base_address: int = 0):
        """Disassemble a binary file containing unSP instructions.
        
        Args:
            input_file: The path to the binary file
            output_file: The path to the output file (optional)
            base_address: The base address for the disassembly
        """
        with open(input_file, 'rb') as f:
            data = f.read()
        
        output = []
        address = base_address
        
        while data:
            instr, size = self.disassemble_instruction(data, address)
            if size == 0:
                break
                
            # Format the output
            output.append(f"{address:08x}: {instr}")
            
            # Advance to the next instruction
            data = data[size:]
            address += size
        
        # Write or print the output
        if output_file:
            with open(output_file, 'w') as f:
                f.write("\n".join(output))
        else:
            print("\n".join(output))


def main():
    parser = argparse.ArgumentParser(description="unSP Disassembler")
    parser.add_argument("input_file", help="The binary file to disassemble")
    parser.add_argument("-o", "--output", help="The output file (defaults to stdout)")
    parser.add_argument("-b", "--base-address", type=lambda x: int(x, 0), default=0,
                        help="The base address for the disassembly (default: 0)")
    parser.add_argument("-j", "--json", default="unsp_instruction_set.json",
                        help="Path to the instruction set JSON file")
    
    args = parser.parse_args()
    
    disassembler = UnSPDisassembler(args.json)
    disassembler.disassemble_file(args.input_file, args.output, args.base_address)


if __name__ == "__main__":
    main()