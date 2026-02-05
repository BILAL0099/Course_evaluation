"""
API endpoints for SCORM course review.
"""

import uuid
import asyncio
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import aiofiles

from config import settings
from src.schemas import (
    UploadResponse, 
    StatusResponse, 
    ReviewReport, 
    ReviewProgress,
    ReviewStatus
)
from src.scorm.extractor import SCORMExtractor
from src.scorm.parser import SCORMParser
from src.agents.orchestrator import ReviewOrchestrator

router = APIRouter()

# In-memory storage for review state (use Redis/DB in production)
reviews: Dict[str, ReviewProgress] = {}
reports: Dict[str, ReviewReport] = {}


@router.post("/upload", response_model=UploadResponse)
async def upload_scorm(file: UploadFile = File(...)):
    """
    Upload a SCORM ZIP package for review.
    
    Returns a review_id to track the review process.
    """
    # Validate file
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    # Generate unique review ID
    review_id = str(uuid.uuid4())[:8]
    
    # Save uploaded file
    upload_path = settings.upload_dir / f"{review_id}.zip"
    
    try:
        async with aiofiles.open(upload_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        file_size = len(content)
        
        # Initialize review progress
        reviews[review_id] = ReviewProgress(
            review_id=review_id,
            status=ReviewStatus.PENDING
        )
        
        return UploadResponse(
            review_id=review_id,
            filename=file.filename,
            file_size=file_size,
            message="Upload successful. Use POST /api/start/{review_id} to begin review."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/start/{review_id}")
async def start_review(review_id: str, background_tasks: BackgroundTasks):
    """
    Start the automated review process for an uploaded SCORM package.
    """
    if review_id not in reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    progress = reviews[review_id]
    
    if progress.status not in [ReviewStatus.PENDING, ReviewStatus.FAILED]:
        raise HTTPException(
            status_code=400, 
            detail=f"Review already {progress.status.value}"
        )
    
    # Start review in background
    background_tasks.add_task(run_review, review_id)
    
    progress.status = ReviewStatus.EXTRACTING
    
    return {
        "review_id": review_id,
        "message": "Review started. Use GET /api/status/{review_id} to check progress."
    }


async def run_review(review_id: str):
    """
    Background task to run the complete review process.
    """
    progress = reviews[review_id]
    
    try:
        from datetime import datetime
        progress.started_at = datetime.utcnow()
        
        # Step 1: Extract SCORM package
        progress.status = ReviewStatus.EXTRACTING
        zip_path = settings.upload_dir / f"{review_id}.zip"
        extract_path = settings.extract_dir / review_id
        
        extractor = SCORMExtractor()
        await extractor.extract(zip_path, extract_path)
        
        # Step 2: Parse manifest
        progress.status = ReviewStatus.PARSING
        parser = SCORMParser()
        manifest = await parser.parse(extract_path)
        
        # Step 3: Run review
        progress.status = ReviewStatus.REVIEWING
        
        orchestrator = ReviewOrchestrator(
            review_id=review_id,
            extract_path=extract_path,
            manifest=manifest,
            progress=progress
        )
        
        report = await orchestrator.run()
        
        # Step 4: Store report
        progress.status = ReviewStatus.COMPLETED
        progress.completed_at = datetime.utcnow()
        reports[review_id] = report
        
    except Exception as e:
        progress.status = ReviewStatus.FAILED
        progress.error_message = str(e)
        import traceback
        traceback.print_exc()


@router.get("/status/{review_id}", response_model=StatusResponse)
async def get_status(review_id: str):
    """
    Get the current status of a review.
    """
    if review_id not in reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    progress = reviews[review_id]
    
    return StatusResponse(
        review_id=review_id,
        status=progress.status,
        progress=progress
    )


@router.get("/report/{review_id}", response_model=ReviewReport)
async def get_report(review_id: str):
    """
    Get the complete review report.
    """
    if review_id not in reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    progress = reviews[review_id]
    
    if progress.status == ReviewStatus.FAILED:
        raise HTTPException(
            status_code=500, 
            detail=f"Review failed: {progress.error_message}"
        )
    
    if progress.status != ReviewStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Review not complete. Current status: {progress.status.value}"
        )
    
    if review_id not in reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return reports[review_id]


@router.delete("/review/{review_id}")
async def delete_review(review_id: str):
    """
    Delete a review and its associated files.
    """
    if review_id not in reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Remove from memory
    del reviews[review_id]
    if review_id in reports:
        del reports[review_id]
    
    # Remove files
    import shutil
    zip_path = settings.upload_dir / f"{review_id}.zip"
    extract_path = settings.extract_dir / review_id
    screenshots_path = settings.screenshots_dir / review_id
    
    if zip_path.exists():
        zip_path.unlink()
    if extract_path.exists():
        shutil.rmtree(extract_path)
    if screenshots_path.exists():
        shutil.rmtree(screenshots_path)
    
    return {"message": f"Review {review_id} deleted successfully"}
