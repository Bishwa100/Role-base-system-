from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
import uuid

from models import SearchRequest, SearchResponse, JobStatus
from database import init_db, create_job, get_job
from tasks import celery_app, scrape_topic_task, AVAILABLE_SOURCES

# Initialize FastAPI app
app = FastAPI(
    title="TopicLens API",
    description="Aggregate resources about any topic from across the internet",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "TopicLens API"}


@app.get("/api/config")
async def get_config():
    """
    Get API configuration and capabilities.
    Returns available search modes and platforms.
    """
    return {
        "search_modes": ["scraping"],
        "default_mode": "scraping",
        "available_sources": AVAILABLE_SOURCES,
        "source_descriptions": {
            "youtube": "YouTube videos and tutorials",
            "github": "GitHub repositories and code projects",
            "reddit": "Reddit communities and discussions",
            "twitter": "Twitter/X posts and threads",
            "blogs": "Blog articles (Medium, Dev.to, etc.)",
            "linkedin": "LinkedIn profiles and posts",
            "facebook": "Facebook groups and pages",
            "instagram": "Instagram accounts and posts",
            "quora": "Quora questions and answers",
            "events": "Events, workshops, and webinars"
        }
    }


@app.get("/api/sources")
async def get_sources():
    """
    Get list of available platforms/sources to search.
    """
    return {
        "sources": [
            {
                "id": "youtube",
                "name": "YouTube",
                "description": "Videos and tutorials",
                "icon": "🎥"
            },
            {
                "id": "github",
                "name": "GitHub",
                "description": "Code repositories and projects",
                "icon": "💻"
            },
            {
                "id": "reddit",
                "name": "Reddit",
                "description": "Communities and discussions",
                "icon": "🗨️"
            },
            {
                "id": "twitter",
                "name": "Twitter/X",
                "description": "Posts, threads, and experts",
                "icon": "🐦"
            },
            {
                "id": "blogs",
                "name": "Blogs",
                "description": "Articles (Medium, Dev.to, etc.)",
                "icon": "📝"
            },
            {
                "id": "linkedin",
                "name": "LinkedIn",
                "description": "Professional profiles and posts",
                "icon": "💼"
            },
            {
                "id": "facebook",
                "name": "Facebook",
                "description": "Groups and pages",
                "icon": "👥"
            },
            {
                "id": "instagram",
                "name": "Instagram",
                "description": "Accounts and posts",
                "icon": "📸"
            },
            {
                "id": "quora",
                "name": "Quora",
                "description": "Questions and answers",
                "icon": "❓"
            },
            {
                "id": "events",
                "name": "Events",
                "description": "Workshops and webinars",
                "icon": "📅"
            }
        ]
    }


@app.post("/api/search", response_model=SearchResponse)
async def start_search(request: SearchRequest):
    """
    Start a new topic search.
    Returns a job_id to poll for results.

    Request body:
        topic: The search topic (required)
        sources: List of platforms to search (optional, default: all platforms)
                 Available: youtube, github, reddit, twitter, blogs, linkedin,
                           facebook, instagram, quora, events
    """
    if not request.topic or len(request.topic.strip()) < 2:
        raise HTTPException(status_code=400, detail="Topic must be at least 2 characters")

    # Validate sources if provided
    sources = request.sources
    if sources:
        # Filter out invalid sources
        valid_sources = [s.lower() for s in sources if s.lower() in AVAILABLE_SOURCES]
        if not valid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"No valid sources provided. Available sources: {', '.join(AVAILABLE_SOURCES)}"
            )
        sources = valid_sources
    else:
        # If no sources specified, use all
        sources = AVAILABLE_SOURCES

    topic = request.topic.strip()
    job_id = str(uuid.uuid4())

    # Create job in database
    create_job(job_id, topic)

    # Dispatch Celery task with selected sources
    scrape_topic_task.apply_async(
        args=[topic, job_id, sources],
        task_id=job_id
    )

    return SearchResponse(job_id=job_id, status="pending")


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """
    Get the status of a search job.
    Returns progress updates or final results.
    """
    # First check Celery task status
    task_result = AsyncResult(job_id, app=celery_app)

    if task_result.state == "PENDING":
        # Check if job exists in database
        db_job = get_job(job_id)
        if db_job:
            return {
                "id": job_id,
                "status": db_job["status"],
                "step": "Queued...",
                "progress": 0
            }
        raise HTTPException(status_code=404, detail="Job not found")

    elif task_result.state == "PROGRESS":
        meta = task_result.info or {}
        return {
            "id": job_id,
            "status": "progress",
            "step": meta.get("step", "Processing..."),
            "progress": meta.get("progress", 0)
        }

    elif task_result.state == "SUCCESS":
        result = task_result.result
        return {
            "id": job_id,
            "status": "done",
            "topic": result.get("topic", ""),
            "insights": result.get("insights", {}),
            "results": result.get("results", {}),
            "total_results": result.get("total_results", 0),
            "counts": result.get("counts", {})
        }

    elif task_result.state == "FAILURE":
        return {
            "id": job_id,
            "status": "error",
            "error": str(task_result.info)
        }

    else:
        return {
            "id": job_id,
            "status": task_result.state.lower(),
            "step": "Processing..."
        }


@app.get("/api/history")
async def get_history(limit: int = 10):
    """
    Get recent search history.
    """
    from database import SessionLocal, SearchJob

    db = SessionLocal()
    try:
        jobs = db.query(SearchJob).order_by(
            SearchJob.created_at.desc()
        ).limit(limit).all()

        return [
            {
                "id": job.id,
                "topic": job.topic,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None
            }
            for job in jobs
        ]
    finally:
        db.close()
