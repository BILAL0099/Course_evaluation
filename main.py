"""
AI Course Reviewer - FastAPI Entry Point

Automated SCORM course testing with functional and content checks.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from endpoints.review import router as review_router

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Automated SCORM e-learning course testing API",
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories for screenshots and reports
app.mount("/screenshots", StaticFiles(directory=str(settings.screenshots_dir)), name="screenshots")
app.mount("/reports", StaticFiles(directory=str(settings.reports_dir)), name="reports")

# Include API routes
app.include_router(review_router, prefix="/api", tags=["Review"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "upload": "POST /api/upload",
            "start": "POST /api/start/{review_id}",
            "status": "GET /api/status/{review_id}",
            "report": "GET /api/report/{review_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
