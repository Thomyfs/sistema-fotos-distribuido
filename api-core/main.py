from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
import httpx, os, json
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

os.makedirs("/storage", exist_ok=True)
app.mount("/images", StaticFiles(directory="/storage"), name="images")

client = MongoClient("mongodb://database-node:27017/")
db = client["photoshare_db"]
photos_col = db["photos"]

active_connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.get("/photos")
def get_photos():
    photos = list(photos_col.find({}, {"_id": 0}).sort("timestamp", -1))
    return photos

@app.post("/upload")
async def upload_photo(author: str = Form(...), caption: str = Form(...), file: UploadFile = File(...)):
    # 1. Comunicación distribuida HTTP hacia el nodo media-worker
    async with httpx.AsyncClient() as http_client:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await http_client.post("http://media-worker:8001/process", files=files)
        worker_data = response.json()

    # 2. Guardar metadatos en el nodo de Base de Datos
    photo_doc = {
        "author": author,
        "caption": caption,
        "url": f"http://localhost:8000/images/{worker_data['filename']}",
        "worker_node": worker_data["processed_by_node"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    photos_col.insert_one(photo_doc.copy())

    # 3. Notificar a todos los usuarios conectados vía WebSockets
    for connection in active_connections:
        await connection.send_text(json.dumps(photo_doc))

    return {"status": "ok", "data": photo_doc}