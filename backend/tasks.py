from celery import Celery
import os

from scrapers.youtube_scraper import scrape_youtube
from scrapers.universal_search_scraper import scrape_blogs, scrape_linkedin, scrape_facebook, scrape_instagram
from scrapers.reddit_scraper import scrape_reddit_communities
from scrapers.eventbrite_scraper import scrape_eventbrite
from scrapers.github_scraper import scrape_github_repos
from scrapers.twitter_scraper import scrape_twitter
from scrapers.quora_scraper import scrape_quora
from scrapers.blog_scraper import scrape_blog_articles
from llm import generate_search_queries, generate_deep_insights, rank_content
from database import save_results

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

# Available platforms for searching
AVAILABLE_SOURCES = [
    "youtube", "github", "reddit", "twitter", "blogs",
    "linkedin", "facebook", "instagram", "quora", "events"
]

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_extended=True,
)


@celery_app.task(bind=True, name="scrape_topic")
def scrape_topic_task(self, topic: str, job_id: str, sources: list = None):
    """
    Main task that orchestrates all scraping/API and LLM operations.

    Args:
        topic: The search topic
        job_id: Unique job identifier
        sources: List of platforms to search (default: all platforms)
    """
    try:
        # If no sources specified, use all available sources
        if not sources:
            sources = AVAILABLE_SOURCES

        # Validate sources
        sources = [s.lower() for s in sources if s.lower() in AVAILABLE_SOURCES]
        if not sources:
            sources = AVAILABLE_SOURCES

        # Step 1: Generate search queries using LLM
        self.update_state(
            state="PROGRESS",
            meta={"step": "Local LLM generating queries...", "progress": 10}
        )
        q = generate_search_queries(topic)

        results = {}

        # Step 2: Scrape Video & Code platforms (if selected)
        if "youtube" in sources or "github" in sources:
            self.update_state(
                state="PROGRESS",
                meta={"step": "Scraping Video & Code...", "progress": 30}
            )
            if "youtube" in sources:
                results["youtube"] = scrape_youtube(q.get("youtube_query", topic))
            if "github" in sources:
                results["github"] = scrape_github_repos(q.get("github_query", topic))

        # Step 3: Scrape Social platforms via search engine (if selected)
        social_sources = [s for s in sources if s in ["linkedin", "facebook", "instagram"]]
        if social_sources:
            self.update_state(
                state="PROGRESS",
                meta={"step": "Scraping Socials via Search Engine...", "progress": 45}
            )
            if "linkedin" in sources:
                results["linkedin"] = scrape_linkedin(q.get("linkedin_query", f"{topic} linkedin"))
            if "facebook" in sources:
                results["facebook"] = scrape_facebook(q.get("facebook_query", f"{topic} facebook groups"))
            if "instagram" in sources:
                results["instagram"] = scrape_instagram(q.get("instagram_query", f"{topic} instagram"))

        # Step 4: Scrape Twitter/X and Quora (if selected)
        if "twitter" in sources or "quora" in sources:
            self.update_state(
                state="PROGRESS",
                meta={"step": "Scraping Twitter & Quora...", "progress": 60}
            )
            if "twitter" in sources:
                results["twitter"] = scrape_twitter(q.get("twitter_query", f"{topic} expert tweets"))
            if "quora" in sources:
                results["quora"] = scrape_quora(q.get("quora_query", f"{topic} questions answers"))

        # Step 5: Scrape Forums, Blogs & Events (if selected)
        content_sources = [s for s in sources if s in ["blogs", "reddit", "events"]]
        if content_sources:
            self.update_state(
                state="PROGRESS",
                meta={"step": "Scraping Blogs, Forums & Events...", "progress": 75}
            )
            if "blogs" in sources:
                results["blogs"] = scrape_blog_articles(q.get("blog_query", f"{topic} tutorial blog"))
            if "reddit" in sources:
                results["reddit"] = scrape_reddit_communities(q.get("reddit_query", topic))
            if "events" in sources:
                results["events"] = scrape_eventbrite(q.get("events_query", f"{topic} workshop"))

        # Step 6: Rank content using LLM
        self.update_state(
            state="PROGRESS",
            meta={"step": "Ranking content using LLM...", "progress": 85}
        )
        ranked_results = rank_content(topic, results)

        # Step 7: Generate deep insights using LLM
        self.update_state(
            state="PROGRESS",
            meta={"step": "Local LLM generating deep insights...", "progress": 95}
        )
        insights = generate_deep_insights(topic, ranked_results)

        # Calculate totals
        counts = {k: len(v) for k, v in ranked_results.items()}

        final_data = {
            "topic": topic,
            "insights": insights,
            "results": ranked_results,
            "total_results": sum(counts.values()),
            "counts": counts,
            "sources_searched": sources
        }

        # Save to database
        save_results(job_id, topic, final_data)

        return final_data

    except Exception as e:
        print(f"[Task Error] {e}")
        # Return minimal data on error
        error_data = {
            "topic": topic,
            "insights": {
                "summary": f"An error occurred while researching {topic}. Please try again.",
                "trends": ["Unable to fetch trends"],
                "action_plan": ["Try searching again"]
            },
            "results": {},
            "total_results": 0,
            "error": str(e)
        }
        save_results(job_id, topic, error_data)
        return error_data
