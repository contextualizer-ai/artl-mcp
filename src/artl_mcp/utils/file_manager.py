"""File management utilities for cross-platform file saving and temp file handling.

This module provides comprehensive file management for ARTL MCP, including:
- Cross-platform path handling
- Configurable output directories
- Temp file management with retention policies
- Safe file naming and sanitization
- Multiple output formats (JSON, text, PDF, etc.)
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml

# Type definitions
FileFormat = Literal["json", "txt", "pdf", "xml", "yaml", "csv"]
RetentionPolicy = Literal[
    "always_delete", "keep_on_error", "always_keep", "user_config"
]


class FileManagerError(Exception):
    """Exception raised for file management errors."""

    pass


class FileManager:
    """Cross-platform file management for scientific literature tools."""

    def __init__(self):
        """Initialize FileManager with default settings."""
        self.temp_dir = self._get_temp_directory()
        self.output_dir = self._get_output_directory()
        self.keep_temp_files = self._get_temp_retention_policy()

    def _get_temp_directory(self) -> Path:
        """Get temp directory from environment or system default."""
        temp_dir_env = os.getenv("ARTL_TEMP_DIR")
        if temp_dir_env:
            temp_dir = Path(temp_dir_env)
            temp_dir.mkdir(parents=True, exist_ok=True)
            return temp_dir
        return Path(tempfile.gettempdir()) / "artl-mcp"

    def _get_output_directory(self) -> Path:
        """Get output directory from environment or default."""
        output_dir_env = os.getenv("ARTL_OUTPUT_DIR")
        if output_dir_env:
            output_dir = Path(output_dir_env)
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir

        # Default to user's documents or home directory
        if os.name == "nt":  # Windows
            documents = Path.home() / "Documents" / "artl-mcp"
        else:  # Unix-like (macOS, Linux)
            documents = Path.home() / "Documents" / "artl-mcp"

        documents.mkdir(parents=True, exist_ok=True)
        return documents

    def _get_temp_retention_policy(self) -> bool:
        """Get temp file retention policy from environment."""
        keep_temp = os.getenv("ARTL_KEEP_TEMP_FILES", "false").lower()
        return keep_temp in ("true", "1", "yes", "on")

    def sanitize_filename(self, filename: str, max_length: int = 200) -> str:
        """Sanitize filename for cross-platform compatibility.

        Args:
            filename: Original filename
            max_length: Maximum filename length

        Returns:
            Sanitized filename safe for all platforms
        """
        # Characters that are problematic on various platforms
        invalid_chars = '<>:"/\\|?*'

        # Replace invalid characters with underscores
        sanitized = "".join("_" if c in invalid_chars else c for c in filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")

        # Handle reserved names on Windows
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

        name_part = sanitized.split(".")[0].upper()
        if name_part in reserved_names:
            sanitized = f"_{sanitized}"

        # Truncate if too long, preserving extension
        if len(sanitized) > max_length:
            if "." in sanitized:
                name, ext = sanitized.rsplit(".", 1)
                name = name[: max_length - len(ext) - 1]
                sanitized = f"{name}.{ext}"
            else:
                sanitized = sanitized[:max_length]

        return sanitized or "unnamed_file"

    def generate_filename(
        self,
        base_name: str,
        identifier: str,
        file_format: FileFormat,
        include_timestamp: bool = True,
    ) -> str:
        """Generate a standardized filename.

        Args:
            base_name: Base name for the file (e.g., "metadata", "fulltext")
            identifier: DOI, PMID, or other identifier
            file_format: File format extension
            include_timestamp: Whether to include timestamp

        Returns:
            Generated filename
        """
        # Clean identifier for use in filename
        clean_id = self.sanitize_filename(
            identifier.replace("/", "_").replace(":", "_")
        )

        # Build filename components
        parts = [base_name, clean_id]

        if include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            parts.append(timestamp)

        filename = "_".join(parts) + f".{file_format}"
        return self.sanitize_filename(filename)

    def save_content(
        self,
        content: Any,
        filename: str,
        file_format: FileFormat,
        output_dir: Path | None = None,
    ) -> Path:
        """Save content to file in specified format.

        Args:
            content: Content to save
            filename: Target filename
            file_format: Format to save in
            output_dir: Directory to save to (defaults to configured output_dir)

        Returns:
            Path to saved file

        Raises:
            FileManagerError: If saving fails
        """
        target_dir = output_dir or self.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / filename

        # Create parent directories for the filename if it contains subdirectories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if file_format == "json":
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=2, ensure_ascii=False, default=str)

            elif file_format == "txt":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

            elif file_format == "pdf":
                # For PDF content (bytes)
                with open(file_path, "wb") as f:
                    f.write(content)

            elif file_format == "xml":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

            elif file_format == "yaml":
                with open(file_path, "w", encoding="utf-8") as f:
                    yaml.dump(content, f, default_flow_style=False, allow_unicode=True)

            elif file_format == "csv":
                # For tabular data
                if isinstance(content, str):
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                else:
                    # Convert dict/list to CSV format
                    import csv

                    with open(file_path, "w", newline="", encoding="utf-8") as f:
                        if (
                            isinstance(content, list)
                            and content
                            and isinstance(content[0], dict)
                        ):
                            writer = csv.DictWriter(f, fieldnames=content[0].keys())
                            writer.writeheader()
                            writer.writerows(content)
                        else:
                            # Fallback to JSON
                            return self.save_content(
                                content,
                                filename.replace(".csv", ".json"),
                                "json",
                                output_dir,
                            )

            else:
                raise FileManagerError(f"Unsupported file format: {file_format}")

            return file_path

        except Exception as e:
            raise FileManagerError(f"Failed to save file {file_path}: {e}") from e

    def create_temp_file(self, suffix: str = "", prefix: str = "artl_") -> Path:
        """Create a temporary file with proper cleanup tracking.

        Args:
            suffix: File suffix/extension
            prefix: File prefix

        Returns:
            Path to temporary file
        """
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Use tempfile to generate unique name but in our temp directory
        fd, temp_path = tempfile.mkstemp(
            suffix=suffix, prefix=prefix, dir=str(self.temp_dir)
        )
        os.close(fd)  # Close the file descriptor, we just want the path

        return Path(temp_path)

    def cleanup_temp_file(self, temp_path: Path, force: bool = False) -> bool:
        """Clean up temporary file based on retention policy.

        Args:
            temp_path: Path to temporary file
            force: Force deletion regardless of policy

        Returns:
            True if file was deleted, False if kept
        """
        if not temp_path.exists():
            return True

        if force or not self.keep_temp_files:
            try:
                temp_path.unlink()
                return True
            except OSError as e:
                # Log cleanup error for debugging purposes
                logging.error(f"Failed to delete temporary file {temp_path}: {e}")

        return False

    def save_with_metadata(
        self,
        content: Any,
        base_name: str,
        identifier: str,
        file_format: FileFormat,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Path]:
        """Save content with optional metadata file.

        Args:
            content: Content to save
            base_name: Base name for files
            identifier: Identifier for filename generation
            file_format: Primary content format
            metadata: Optional metadata to save alongside

        Returns:
            Dictionary mapping 'content' and optionally 'metadata' to file paths
        """
        # Generate filenames
        content_filename = self.generate_filename(base_name, identifier, file_format)

        # Save main content
        content_path = self.save_content(content, content_filename, file_format)

        result = {"content": content_path}

        # Save metadata if provided
        if metadata:
            metadata_filename = self.generate_filename(
                f"{base_name}_metadata", identifier, "json"
            )
            metadata_path = self.save_content(metadata, metadata_filename, "json")
            result["metadata"] = metadata_path

        return result

    def stream_download_to_file(
        self,
        url: str,
        filename: str,
        file_format: FileFormat,
        output_dir: Path | None = None,
        chunk_size: int = 8192,
        headers: dict[str, str] | None = None,
    ) -> tuple[Path, int]:
        """Stream download content directly to file to avoid loading into memory.

        Args:
            url: URL to download from
            filename: Target filename
            file_format: File format (determines write mode)
            output_dir: Directory to save to (defaults to output_dir)
            chunk_size: Size of chunks to read/write (default 8KB)
            headers: Optional HTTP headers for request

        Returns:
            Tuple of (file_path, total_bytes_downloaded)

        Raises:
            FileManagerError: If download or saving fails
        """
        import requests

        target_dir = output_dir or self.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        total_bytes = 0
        write_mode = "wb" if file_format == "pdf" else "w"
        encoding = None if file_format == "pdf" else "utf-8"

        try:
            with requests.get(
                url, headers=headers or {}, stream=True, timeout=60
            ) as response:
                response.raise_for_status()

                with open(file_path, write_mode, encoding=encoding) as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:  # filter out keep-alive chunks
                            if file_format == "pdf":
                                f.write(chunk)
                            else:
                                f.write(chunk.decode("utf-8", errors="replace"))
                            total_bytes += len(chunk)

            return file_path, total_bytes

        except Exception as e:
            # Clean up partial file on error
            if file_path.exists():
                file_path.unlink(missing_ok=True)
            raise FileManagerError(
                f"Failed to stream download {url} to {file_path}: {e}"
            ) from e

    def handle_file_save(
        self,
        content: Any,
        base_name: str,
        identifier: str,
        file_format: FileFormat,
        save_file: bool = False,
        save_to: str | Path | None = None,
        use_temp_dir: bool = True,
    ) -> Path | None:
        """Handle file saving with simplified interface.

        Args:
            content: Content to save
            base_name: Base name for file
            identifier: Identifier for filename generation
            file_format: File format
            save_file: Save to default location (temp dir if use_temp_dir=True)
            save_to: Specific path to save to (overrides save_file)
            use_temp_dir: Use temp directory for default saves

        Returns:
            Path to saved file or None if no saving requested
        """
        # If save_to is specified, always save there
        if save_to is not None:
            save_path = Path(save_to)

            # If it's a relative path (just a filename), save relative to output_dir
            if not save_path.is_absolute():
                save_path = self.output_dir / save_path

            # Ensure the filename has the correct extension
            filename = save_path.name
            if not filename.endswith(f".{file_format}"):
                filename = f"{filename}.{file_format}"
                save_path = save_path.parent / filename

            # Ensure directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)
            return self.save_content(
                content, save_path.name, file_format, save_path.parent
            )

        # If save_file is True, save to default location
        if save_file:
            filename = self.generate_filename(base_name, identifier, file_format)
            target_dir = self.temp_dir if use_temp_dir else self.output_dir
            return self.save_content(content, filename, file_format, target_dir)

        # No saving requested
        return None


# Global instance for easy access
file_manager = FileManager()


# Convenience functions
def save_json(content: Any, filename: str, output_dir: Path | None = None) -> Path:
    """Save content as JSON file."""
    return file_manager.save_content(content, filename, "json", output_dir)


def save_text(content: str, filename: str, output_dir: Path | None = None) -> Path:
    """Save content as text file."""
    return file_manager.save_content(content, filename, "txt", output_dir)


def save_pdf(content: bytes, filename: str, output_dir: Path | None = None) -> Path:
    """Save content as PDF file."""
    return file_manager.save_content(content, filename, "pdf", output_dir)


def get_safe_filename(base_name: str, identifier: str, extension: FileFormat) -> str:
    """Generate a safe filename for any platform."""
    return file_manager.generate_filename(base_name, identifier, extension)
