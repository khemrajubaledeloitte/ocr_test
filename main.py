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

# Enable CORS for all origins (adjust if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize PaddleOCR
ocr_paddle = PaddleOCR(
    use_angle_cls=False,
    lang='en',
    det_db_box_thresh=0.5,
    rec_algorithm='CRNN',
)

# ✅ Health check route
@app.get("/")
def root():
    return {"message": "OCR API is running. Visit /docs for Swagger UI."}

# ✅ Tesseract endpoint
@app.post("/extract-text/")
async def extract_text_from_image(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image)
        return {"filename": file.filename, "extracted_text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ✅ PaddleOCR endpoint
@app.post("/extract-text-paddle/")
async def extract_text_with_paddleocr(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpeg") as tmp:
            tmp.write(image_data)
            image_path = tmp.name

        result = ocr_paddle.ocr(image_path)
        # ✅ Fixed: parse correctly
        extracted_text = [line[1][0] for line in result[0]] if result and isinstance(result[0], list) else []

        structured = extract_invoice_fields_v2(extracted_text)
        return {
            "filename": os.path.basename(file.filename),
            "extracted_text": extracted_text,
            "structured_data": structured
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        try:
            os.remove(image_path)
        except:
            pass

# ✅ Custom error handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )

# ✅ Extraction helpers

def extract_invoice_fields(text_lines):
    data = {
        "invoice_total": None,
        "invoice_number": None,
        "date_of_issue": None
    }

    for line in text_lines:
        if not data["invoice_total"] and ("total" in line.lower() or "due" in line.lower()):
            match = re.search(r"\$[\d,]+\.\d{2}", line)
            if match:
                data["invoice_total"] = match.group()

        if not data["invoice_number"]:
            match = re.search(r"invoice.*?(\d{5,8})", line.lower())
            if match:
                data["invoice_number"] = match.group(1)

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

        if not data["company_name"] and "company name" in line_lower:
            data["company_name"] = line.strip()

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

        if capture_bill_to:
            data["bill_to"].append(line.strip())

        if capture_ship_to:
            data["ship_to"].append(line.strip())

        if not data["invoice_number"]:
            match = re.search(r"invoice.*?(\d{5,8})", line_lower)
            if match:
                data["invoice_number"] = match.group(1)

        if not data["date_of_issue"]:
            match = re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", line)
            if match:
                data["date_of_issue"] = match.group()

        if not data["invoice_total"] and "total" in line_lower:
            match = re.search(r"\$[\d,.]+\b", line)
            if match:
                data["invoice_total"] = match.group()

        if "description" in line_lower and "amount" in line_lower:
            capture_items = True
            continue
        if capture_items:
            if "$" in line or re.search(r"\$\s*\d+", line):
                data["amounts"].append(line.strip())
            elif line.strip():
                data["description"].append(line.strip())

    return data
