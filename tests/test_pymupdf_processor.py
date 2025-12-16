#!/usr/bin/env python3

import asyncio
from pathlib import Path
from grag.ingestion.vision.pymupdf_processor import PyMuPDFProcessor

async def test_pymupdf():
    try:
        print("Testing PyMuPDF processor...")

        # Create processor
        processor = PyMuPDFProcessor()
        print("PyMuPDF processor created successfully")

        # Test with PDF file
        pdf_path = Path("/Users/rex/Desktop/stimOn.2025.04.01/Predicate_K161091/K161091.pdf")
        if pdf_path.exists():
            print(f"Processing PDF: {pdf_path.name}")

            # Process document
            result = await asyncio.get_event_loop().run_in_executor(None, processor.process_document, pdf_path, "test_id", "test_area")

            print(f"Processing completed in {result.processing_time:.2f}s")
            print(f"Extracted text length: {len(result.ocr_text)}")
            print(f"Number of regions: {len(result.regions)}")
            print(f"Number of tables: {len(result.tables)}")
            print(f"Number of charts: {len(result.charts)}")

            # Show first 500 characters of text
            if result.ocr_text:
                print("\nFirst 500 characters of extracted text:")
                print(result.ocr_text[:500])
                print("...")
            else:
                print("No text extracted!")

        else:
            print(f"PDF file not found: {pdf_path}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pymupdf())
