"""
API routes for research topic management.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from src.services.mongodb_service import MongoDBService, get_mongodb
from src.models.research import ResearchTopic, ResearchTopicCreate, ResearchTopicUpdate, ResearchTopicResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ================== CREATE RESEARCH ==================
@router.post("/researches", response_model=ResearchTopicResponse, status_code=201)
async def create_research(
    research: ResearchTopicCreate,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    """Create a new research topic."""
    try:
        research_id = await mongodb.create_research(
            name=research.name,
            description=research.description,
            papers=research.papers,
            tags=research.tags
        )

        # Retrieve and return the created research
        created_research = await mongodb.get_research(research_id)
        if created_research:
            logger.info(f"✅ Created research: {research_id}")
            return created_research
        else:
            raise HTTPException(status_code=500, detail="Failed to create research")

    except Exception as e:
        logger.error(f"Error creating research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ================== GET ALL RESEARCHES ==================
@router.get("/researches", response_model=List[ResearchTopicResponse])
async def get_all_researches(
    include_archived: bool = False,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    """Retrieve all research topics."""
    try:
        researches = await mongodb.get_all_researches(include_archived=include_archived)
        logger.info(f"✅ Retrieved {len(researches)} researches")
        return researches

    except Exception as e:
        logger.error(f"Error retrieving researches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ================== GET SINGLE RESEARCH ==================
@router.get("/researches/{research_id}", response_model=ResearchTopicResponse)
async def get_research(
    research_id: str,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    """Retrieve a specific research topic."""
    try:
        research = await mongodb.get_research(research_id)
        if not research:
            raise HTTPException(status_code=404, detail="Research topic not found")

        logger.info(f"✅ Retrieved research: {research_id}")
        return research

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ================== UPDATE RESEARCH ==================
@router.put("/researches/{research_id}", response_model=ResearchTopicResponse)
async def update_research(
    research_id: str,
    research: ResearchTopicUpdate,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    """Update a research topic."""
    try:
        success = await mongodb.update_research(
            research_id=research_id,
            name=research.name,
            description=research.description,
            papers=research.papers,
            tags=research.tags,
            is_archived=research.is_archived
        )

        if not success:
            raise HTTPException(status_code=404, detail="Research topic not found")

        # Retrieve and return the updated research
        updated_research = await mongodb.get_research(research_id)
        if updated_research:
            logger.info(f"✅ Updated research: {research_id}")
            return updated_research
        else:
            raise HTTPException(status_code=500, detail="Failed to update research")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ================== ADD PAPER TO RESEARCH ==================
@router.post("/researches/{research_id}/papers/{paper_id}", status_code=200)
async def add_paper_to_research(
    research_id: str,
    paper_id: str,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    """Add a paper to a research topic."""
    try:
        success = await mongodb.add_paper_to_research(research_id, paper_id)

        if not success:
            raise HTTPException(status_code=404, detail="Research topic not found")

        logger.info(f"✅ Added paper {paper_id} to research {research_id}")
        return {"message": "Paper added successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding paper to research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ================== REMOVE PAPER FROM RESEARCH ==================
@router.delete("/researches/{research_id}/papers/{paper_id}", status_code=200)
async def remove_paper_from_research(
    research_id: str,
    paper_id: str,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    """Remove a paper from a research topic."""
    try:
        success = await mongodb.remove_paper_from_research(research_id, paper_id)

        if not success:
            raise HTTPException(status_code=404, detail="Research topic not found")

        logger.info(f"✅ Removed paper {paper_id} from research {research_id}")
        return {"message": "Paper removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing paper from research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ================== DELETE RESEARCH ==================
@router.delete("/researches/{research_id}", status_code=200)
async def delete_research(
    research_id: str,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    """Delete a research topic and its chat history."""
    try:
        success = await mongodb.delete_research(research_id)

        if not success:
            raise HTTPException(status_code=404, detail="Research topic not found")

        logger.info(f"✅ Deleted research: {research_id}")
        return {"message": "Research topic deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
