import tempfile

import requests
import os
from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError


def extract_text_from_pdf(pdf_url: str) -> str:
    """
    Download and extract text from a PDF given its URL, using a temporary file.
    """
    response = requests.get(pdf_url)
    if response.status_code != 200:
        return "Error: Unable to retrieve PDF."

    temp_pdf_path = None
    text_results = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(response.content)
            temp_pdf.flush()  # Ensure all data is written before reading

            temp_pdf_path = temp_pdf.name
            text = extract_text(temp_pdf_path)
            text_results = text.strip() if text else "Error: No text extracted from PDF."

    except (OSError, PDFSyntaxError) as e:
        return f"Error extracting PDF text: {e}"

    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

    return text_results
