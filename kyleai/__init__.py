from binaryninja.architecture import Architecture, InstructionInfo, InstructionTextToken, InstructionTextTokenType
from binaryninja.enums import BranchType, Endianness

class UnSP(Architecture):
    name = "unSP"
    address_size = 4
    default_int_size = 4
    max_instr_length = 4  # unSP uses fixed 32-bit instructions

    # Registers as defined in the SLEIGH specification:
    regs = {
        "r0": 0,  "r1": 1,  "r2": 2,  "r3": 3,
        "r4": 4,  "r5": 5,  "r6": 6,  "r7": 7,
        "r8": 8,  "r9": 9,  "r10": 10, "r11": 11,
        "r12": 12, "r13": 13, "r14": 14, "r15": 15,
        "pc": 16, "sp": 17, "psw": 18,
    }
    stack_pointer = "sp"
    endianness = Endianness.LittleEndian

    # The following opcode mappings follow the unSP SLEIGH specification.
    # For example:
    #   0x00 => nop
    #   0x10 => mov rD, rS, with rD in low nibble and rS in high nibble of the second byte.
    #   0x20 => movi rD, imm16, with rD in low nibble of the second byte and a 16-bit immediate in bytes 2–3.

    def get_instruction_info(self, data, addr):
        if len(data) < 4:
            return None
        info = InstructionInfo()
        info.length = 4

        # Example: if a branch instruction is decoded,
        # set info.add_branch(BranchType.TrueBranch, target) accordingly.
        opcode = data[0]
        # (Expand with branch target calculations if needed.)
        return info

    def get_instruction_text(self, data, addr):
        tokens = []
        if len(data) < 4:
            tokens.append(InstructionTextToken(InstructionTextTokenType.TextToken, "invalid"))
            return tokens, 1

        opcode = data[0]
        if opcode == 0x00:
            tokens.append(InstructionTextToken(InstructionTextTokenType.InstructionToken, "nop"))
        elif opcode == 0x10:
            # According to the unSP SLEIGH spec, MOV is encoded in a single byte:
            # data[1]: lower 4 bits = destination (rD), upper 4 bits = source (rS)
            rd = data[1] & 0x0F
            rs = (data[1] >> 4) & 0x0F
            tokens.append(InstructionTextToken(InstructionTextTokenType.InstructionToken, "mov"))
            tokens.append(InstructionTextToken(InstructionTextTokenType.OperandSeparatorToken, " "))
            tokens.append(InstructionTextToken(InstructionTextTokenType.RegisterToken, f"r{rd}"))
            tokens.append(InstructionTextToken(InstructionTextTokenType.OperandSeparatorToken, ", "))
            tokens.append(InstructionTextToken(InstructionTextTokenType.RegisterToken, f"r{rs}"))
        elif opcode == 0x20:
            # MOVI instruction: destination register is in the low nibble of data[1],
            # immediate is stored in bytes 2 and 3 (little-endian)
            rd = data[1] & 0x0F
            imm = int.from_bytes(data[2:4], byteorder="little")
            tokens.append(InstructionTextToken(InstructionTextTokenType.InstructionToken, "movi"))
            tokens.append(InstructionTextToken(InstructionTextTokenType.OperandSeparatorToken, " "))
            tokens.append(InstructionTextToken(InstructionTextTokenType.RegisterToken, f"r{rd}"))
            tokens.append(InstructionTextToken(InstructionTextTokenType.OperandSeparatorToken, ", "))
            tokens.append(InstructionTextToken(InstructionTextTokenType.IntegerToken, f"{imm:#x}", value=imm))
        else:
            tokens.append(InstructionTextToken(InstructionTextTokenType.TextToken, "unknown"))
        return tokens, 4

    def get_instruction_low_level_il(self, data, addr, il):
        if len(data) < 4:
            return None
        opcode = data[0]
        if opcode == 0x00:
            # nop – no operation
            return il.no_expr()
        elif opcode == 0x10:
            # mov rD, rS
            rd = data[1] & 0x0F
            rs = (data[1] >> 4) & 0x0F
            return il.set_reg(4, f"r{rd}", il.reg(4, f"r{rs}"))
        elif opcode == 0x20:
            # movi rD, imm16
            rd = data[1] & 0x0F
            imm = int.from_bytes(data[2:4], byteorder="little")
            return il.set_reg(4, f"r{rd}", il.const(4, imm))
        # (Implement additional opcodes per the SLEIGH spec as needed.)
        return None

# Register the unSP architecture with Binary Ninja.
UnSP.register()
