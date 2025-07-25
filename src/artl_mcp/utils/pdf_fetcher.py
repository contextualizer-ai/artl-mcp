import requests
from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError

from artl_mcp.utils.file_manager import file_manager


def extract_text_from_pdf(pdf_url: str) -> str:
    """
    Download and extract text from a PDF given its URL, using FileManager temp files.
    """
    try:
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return "Error: Unable to retrieve PDF."
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError,
        ConnectionError,
    ) as e:
        return f"Error: Network error while retrieving PDF: {e}"

    temp_pdf_path = None
    text_results = None

    try:
        # Use FileManager for consistent temp file handling
        temp_pdf_path = file_manager.create_temp_file(
            suffix=".pdf", prefix="pdf_extract_"
        )
        temp_pdf_path.write_bytes(response.content)

        text = extract_text(str(temp_pdf_path))
        text_results = text.strip() if text else "Error: No text extracted from PDF."

    except (OSError, PDFSyntaxError) as e:
        return f"Error extracting PDF text: {e}"

    finally:
        if temp_pdf_path:
            file_manager.cleanup_temp_file(temp_pdf_path)

    return text_results
