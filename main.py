from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    message = fetch_instagram_insights()  # Call the function from untitled49.py
    return {"message": message}
