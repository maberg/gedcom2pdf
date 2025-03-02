A Python script that converts a GEDCOM file (a standard format for genealogical data) to a PDF file using the gedcom library for parsing and reportlab for creating the PDF output

A pre-processing stage will attempt to repair errors in the input GEDCOM file such as level number jumping, invalid characters and XML-tags

Before running this code, you need to install the required libraries: pip install reportlab python-gedcom

Usage: python ged2pdf.py [-h] input_file output_file

Convert a GEDCOM file to a PDF file, repairing line numbering and sanitizing
data.

positional arguments:
  input_file   Path to the input GEDCOM file (e.g., family.ged)
  output_file  Path to the output PDF file (e.g., output.pdf)

optional arguments:
  -h, --help   show this help message and exit
