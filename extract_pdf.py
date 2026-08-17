import fitz
import os
import json

doc = fitz.open("ImageToPDF 16-08-2026 19.21.17.pdf")
os.makedirs("pdf_pages", exist_ok=True)

print(f"Total pages: {len(doc)}")

page_texts = {}
for i, page in enumerate(doc):
    text = page.get_text()
    page_texts[i + 1] = text
    print(f"Page {i + 1}: text length = {len(text.strip())}")
    pix = page.get_pixmap(dpi=150)
    pix.save(f"pdf_pages/page_{i + 1}.png")

with open("pdf_pages/extracted_text.json", "w", encoding="utf-8") as f:
    json.dump(page_texts, f, indent=2, ensure_ascii=False)

print("Finished extracting all pages and text.")
