import os
import json
import secrets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Simulated Database for User IDs and Passwords
USER_DB = {
    "player1": "pass123",
    "player2": "secure456",
    "guest": "valorant"
}

# Matchmaking Rooms state tracker
# Structure: { room_id: { player_id: { "websocket": ws, "x": 0, "y": 0, "z": 0 } } }
rooms = {}

@app.get("/")
def get_game():
    # Serves the main game interface
    return FileResponse("templates/index.html")

@app.websocket("/ws/{room_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str):
    await websocket.accept()
    
    # Initialize room if it doesn't exist
    if room_id not in rooms:
        rooms[room_id] = {}
        
    # Add player session data
    rooms[room_id][username] = {
        "websocket": websocket,
        "x": 0, "y": 1.6, "z": 0,
        "agent": "jett"
    }
    
    # Notify everyone in the room about the new player
    await broadcast_to_room(room_id, {
        "type": "player_joined",
        "username": username
    })

    try:
        while True:
            # Listen to incoming movement, shooting, or ability data from browser
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "move":
                rooms[room_id][username]["x"] = message["x"]
                rooms[room_id][username]["y"] = message["y"]
                rooms[room_id][username]["z"] = message["z"]
                rooms[room_id][username]["ry"] = message["ry"]
                
                # Relay positional data to all other players in the lobby
                await broadcast_to_room(room_id, {
                    "type": "update",
                    "username": username,
                    "x": message["x"],
                    "y": message["y"],
                    "z": message["z"],
                    "ry": message["ry"]
                }, exclude=username)
                
            elif message["type"] == "ability":
                # Broadcast Valorant ability triggers (e.g., Jett smoke, Sage wall)
                await broadcast_to_room(room_id, {
                    "type": "ability_cast",
                    "username": username,
                    "ability": message["ability"]
                }, exclude=username)

    except WebSocketDisconnect:
        # Clean up room memory when a friend leaves or closes the tab
        if room_id in rooms and username in rooms[room_id]:
            del rooms[room_id][username]
            if not rooms[room_id]: # Delete room if entirely empty
                del rooms[room_id]
            else:
                await broadcast_to_room(room_id, {
                    "type": "player_left",
                    "username": username
                })

async def broadcast_to_room(room_id: str, message: dict, exclude: str = None):
    """Helper function to send JSON packages to everyone inside a specific room."""
    if room_id in rooms:
        for user, data in list(rooms[room_id].items()):
            if user != exclude:
                try:
                    await data["websocket"].send_json(message)
                except Exception:
                    pass

if __name__ == "__main__":
    import uvicorn
    # Read environment port for cloud hosting environments
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
