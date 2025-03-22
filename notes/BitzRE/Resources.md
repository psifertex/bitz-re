IDE, example code:
https://www.generalplus.com/GPCE100A-37a-1LVPVz2LN4836SVpnSNproduct_detail#

Related repo:
https://github.com/GMMan/punitapichan-notes/tree/master


### Stream Summaries:

#### 2025-03-21
First stream we identified the CPU based on the firmware dump, found several existing tools, extracted the opcode table from the PDF (lots of manual fixups of the tables!) and created a basic [disassembler](../arch/unsp_disassembler.py). Used claude for most of the code generation and creation of the json instruction specification. 