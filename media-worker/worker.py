from fastapi import FastAPI, UploadFile, File
from PIL import Image
import io, os, uuid, socket

app = FastAPI()
STORAGE_DIR = "/storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.thumbnail((800, 800))

    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(STORAGE_DIR, filename)
    image.save(filepath, "JPEG", quality=85)

    # Retornamos el ID del contenedor para evidenciar qué nodo procesó la foto
    return {
        "filename": filename,
        "processed_by_node": socket.gethostname()
    }