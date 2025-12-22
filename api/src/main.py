from uvicorn import run

if __name__ == "__main__":
    run("v1.app:app", host="localhost", port=8000, reload=True)