import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.head("/")
@app.get("/")
def get_game():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path_1 = os.path.join(base_dir, "index.html")
    html_path_2 = os.path.abspath("index.html")
    html_path_3 = os.path.join(base_dir, "templates", "index.html")

    if os.path.exists(html_path_1):
        return FileResponse(html_path_1)
    elif os.path.exists(html_path_2):
        return FileResponse(html_path_2)
    elif os.path.exists(html_path_3):
        return FileResponse(html_path_3)
        
    return JSONResponse(
        status_code=404,
        content={
            "error": "index.html not found",
            "looked_in_path_1": html_path_1,
            "looked_in_path_2": html_path_2,
            "current_working_directory": os.getcwd()
        }
    )

rooms = {}

@app.websocket("/ws/{room_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str):
    await websocket.accept()
    
    if room_id not in rooms:
        rooms[room_id] = {}
        
    rooms[room_id][username] = {
        "websocket": websocket,
        "x": 0, "y": 1.6, "z": 0, "ry": 0
    }
    
    await broadcast_to_room(room_id, {
        "type": "player_joined",
        "username": username
    })

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "move":
                if room_id in rooms and username in rooms[room_id]:
                    rooms[room_id][username]["x"] = message["x"]
                    rooms[room_id][username]["y"] = message["y"]
                    rooms[room_id][username]["z"] = message["z"]
                    rooms[room_id][username]["ry"] = message["ry"]
                
                await broadcast_to_room(room_id, {
                    "type": "update",
                    "username": username,
                    "x": message["x"],
                    "y": message["y"],
                    "z": message["z"],
                    "ry": message["ry"]
                }, exclude=username)
                
            elif message["type"] == "ability":
                await broadcast_to_room(room_id, {
                    "type": "ability_cast",
                    "username": username,
                    "ability": message["ability"]
                }, exclude=username)

    except WebSocketDisconnect:
        if room_id in rooms and username in rooms[room_id]:
            del rooms[room_id][username]
            if not rooms[room_id]:
                del rooms[room_id]
            else:
                await broadcast_to_room(room_id, {
                    "type": "player_left",
                    "username": username
                })

async def broadcast_to_room(room_id: str, message: dict, exclude: str = None):
    if room_id in rooms:
        for user, data in list(rooms[room_id].items()):
            if user != exclude:
                try:
                    await data["websocket"].send_json(message)
                except Exception:
                    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
