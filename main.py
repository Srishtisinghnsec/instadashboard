from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    username=input("enter your username")
    password=input("enter your password")
    message = fetch_instagram_insights(username,password)  # Call the function from untitled49.py
    return {"message": message}
