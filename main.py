from fastapi import FastAPI, File, UploadFile, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract
import io
from paddleocr import PaddleOCR
import tempfile
import os
import re

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Initialize PaddleOCR once
ocr_paddle = ocr_paddle = PaddleOCR(
    use_angle_cls=False,   # <--- turn this off to save RAM
    lang='en',
    det_db_box_thresh=0.5,  # optional: increase this to reduce box count
    rec_algorithm='CRNN',   # optional: lighter model
)


# Set this for Windows systems if Tesseract is not in PATH

@app.post("/extract-text/")
async def extract_text_from_image(file: UploadFile = File(...)):
    print("Received request to /extract-text/")
    
    try:
        print(f"Reading uploaded file: {file.filename}")
        image_data = await file.read()

        print("Opening image with PIL...")
        image = Image.open(io.BytesIO(image_data))

        print("Extracting text with pytesseract...")
        text = pytesseract.image_to_string(image)

        print(f"Extraction complete. Text extracted from {file.filename}")
        return {"filename": file.filename, "extracted_text": text}
    
    except Exception as e:
        print(f"Error occurred during processing: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Validation error occurred: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


import re

def extract_invoice_fields(text_lines):
    data = {
        "invoice_total": None,
        "invoice_number": None,
        "date_of_issue": None
    }

    for line in text_lines:
        # Extract total using context (total, due)
        if not data["invoice_total"] and ("total" in line.lower() or "due" in line.lower()):
            match = re.search(r"\$[\d,]+\.\d{2}", line)
            if match:
                data["invoice_total"] = match.group()

        # Extract invoice number using keyword
        if not data["invoice_number"]:
            match = re.search(r"invoice.*?(\d{5,8})", line.lower())
            if match:
                data["invoice_number"] = match.group(1)

        # Extract date
        if not data["date_of_issue"]:
            match = re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", line)
            if match:
                data["date_of_issue"] = match.group()

    return data

def extract_invoice_fields_v2(text_lines):
    data = {
        "company_name": None,
        "bill_to": [],
        "ship_to": [],
        "invoice_number": None,
        "date_of_issue": None,
        "invoice_total": None,
        "description": [],
        "amounts": []
    }

    capture_bill_to = False
    capture_ship_to = False
    capture_items = False

    for line in text_lines:
        line_lower = line.lower()

        # Company name (first line)
        if not data["company_name"] and "company name" in line_lower:
            data["company_name"] = line.strip()

        # Start capturing BILL TO block
        if "bill to" in line_lower or "billto" in line_lower:
            capture_bill_to = True
            capture_ship_to = False
            continue
        elif "ship to" in line_lower:
            capture_ship_to = True
            capture_bill_to = False
            continue
        elif any(kw in line_lower for kw in ["description", "amount", "subtotal", "tax", "total"]):
            capture_bill_to = False
            capture_ship_to = False

        # Collect billing address lines
        if capture_bill_to:
            data["bill_to"].append(line.strip())

        # Collect shipping address lines
        if capture_ship_to:
            data["ship_to"].append(line.strip())

        # Extract invoice number
        if not data["invoice_number"]:
            match = re.search(r"invoice.*?(\d{5,8})", line_lower)
            if match:
                data["invoice_number"] = match.group(1)

        # Extract date
        if not data["date_of_issue"]:
            match = re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", line)
            if match:
                data["date_of_issue"] = match.group()

        # Extract invoice total (contextual)
        if not data["invoice_total"] and "total" in line_lower:
            match = re.search(r"\$[\d,.]+\b", line)
            if match:
                data["invoice_total"] = match.group()

        # Start item table capture
        if "description" in line_lower and "amount" in line_lower:
            capture_items = True
            continue
        if capture_items:
            if "$" in line or re.search(r"\$\s*\d+", line):
                data["amounts"].append(line.strip())
            elif line.strip():
                data["description"].append(line.strip())

    return data


@app.post("/extract-text-paddle/")
async def extract_text_with_paddleocr(file: UploadFile = File(...)):
    try:
        print(f"Reading uploaded file: {file.filename}")
        image_data = await file.read()

        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpeg") as tmp:
            tmp.write(image_data)
            image_path = tmp.name

        print(f"Running PaddleOCR on image: {image_path}")
        result = ocr_paddle.ocr(image_path)
        print("PaddleOCR raw result:", result)

        extracted_text = result[0]['rec_texts']  # ✅ corrected structure
        # structured = extract_invoice_fields(extracted_text)
        structured = extract_invoice_fields_v2(extracted_text)


        return {
            "filename": os.path.basename(file.filename),
            "extracted_text": extracted_text,
            "structured_data": structured
        }

    except Exception as e:
        print(f"Error during PaddleOCR processing: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        try:
            os.remove(image_path)
        except:
            pass
