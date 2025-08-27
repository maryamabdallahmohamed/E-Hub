import asyncio
import websockets

async def chat():
    uri = "ws://localhost:8000/ws/chat"
    async with websockets.connect(uri) as websocket:
        print("Connected to chat. Type 'exit' to quit.")
        while True:
            message = input("You: ")
            if message.lower() == "exit":
                break
            await websocket.send(message)

            # Receive streaming chunks
            while True:
                response = await websocket.recv()
                if response == "[DONE]":
                    break
                print("Gemini:", response)

if __name__ == "__main__":
    asyncio.run(chat())
