from fastapi import FastAPI, File, UploadFile, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from PIL import Image
import pytesseract
import io
import platform

app = FastAPI()

# Set Tesseract command based on OS
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    # On Linux (Render), Tesseract should be in PATH by default, so no need to set explicitly
    # But you can set it explicitly if needed, e.g.:
    # pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
    pass

@app.post("/extract-text/")
async def extract_text_from_image(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image)
        return {"filename": file.filename, "extracted_text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )
