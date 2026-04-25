import base64
import logging
from pathlib import Path

from app.config import settings
from app.llm.client import generate

logger = logging.getLogger(__name__)

_OCR_SYSTEM_PROMPT = "You are an OCR engine. Extract all text from the provided image. Return only the extracted text, no commentary or formatting instructions."


async def extract_text_multimodal(image_path: Path, model: str | None = None) -> str:
    """Extract text from an image using a multimodal LLM via the central client."""
    resolved_model = model or settings.vision_model
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return await generate(
        system_prompt=_OCR_SYSTEM_PROMPT,
        user_content="Extract all text from this image.",
        model=resolved_model,
        images=[image_b64],
    )

def extract_text_tesseract(image_path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)
    except ImportError:
        raise RuntimeError("pytesseract or Pillow not installed — cannot use Tesseract fallback")
    except Exception as e:
        raise RuntimeError(f"Tesseract OCR failed: {e}")

async def extract_text_from_image(image_path: Path, prefer_multimodal: bool = True, model: str | None = None) -> str:
    model = model or settings.vision_model
    if prefer_multimodal:
        try:
            return await extract_text_multimodal(image_path, model)
        except Exception:
            pass
    return extract_text_tesseract(image_path)

async def extract_text_from_scanned_pdf(pdf_path: Path, prefer_multimodal: bool = True, model: str | None = None) -> list[dict]:
    model = model or settings.vision_model
    import io
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber required for scanned PDF processing")
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            img = page.to_image(resolution=200)
            img_bytes = io.BytesIO()
            img.original.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img_bytes.read())
                tmp_path = Path(tmp.name)
            try:
                text = await extract_text_from_image(tmp_path, prefer_multimodal, model)
            finally:
                tmp_path.unlink(missing_ok=True)
            pages.append({"text": text, "page_number": i})
    return pages
