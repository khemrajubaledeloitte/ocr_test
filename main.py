from fastapi import FastAPI, File, UploadFile, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from PIL import Image
import pytesseract
import io

app = FastAPI()

# Set this for Windows systems if Tesseract is not in PATH
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\\Tesseract-OCR\tesseract.exe'

@app.post("/extract-text/")
async def extract_text_from_image(file: UploadFile = File(...)):
    try:
        # Read image file
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))

        # Extract text using pytesseract
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
