from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {
        "message": "Hello World"
    }

@app.post("/users")
def get_users():
    return [
        {"id":1, "name":"Alice", "age":18},
        {"id":2, "name":"Bob", "age":20}
        ]

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)