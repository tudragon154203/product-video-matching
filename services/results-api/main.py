import sys
import os

# Add the app directory to the Python path for bind mount setup
sys.path.append("/app/app")

from handlers.results_handler import ResultsHandler
import uvicorn

if __name__ == "__main__":
    handler = ResultsHandler()
    uvicorn.run(handler.app, host="0.0.0.0", port=8080)
