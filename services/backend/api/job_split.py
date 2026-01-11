from typing import Any, Dict

from db.session import get_db
from fastapi import APIRouter, Body, Depends, FastAPI, Path, Query
from schema.job_split import (
    JobSplit,
    ListJobSplitRequest,
    ListJobSplitResponse,
    UpdateJobSplitRequest,
)
from service.job_split import JobSplitService
from sqlalchemy.orm import Session

job_split_router = APIRouter()


@job_split_router.get("/{job_id}", response_model=ListJobSplitResponse, summary="任务列表")
def list_job_splitss(
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1),
    db: Session = Depends(get_db)
) -> ListJobSplitResponse:
    """
    列出任务片段
    """
    service = JobSplitService(db)
    result = service.list_job_splits(page, page_size)
    # Convert db.models.JobSplit objects to schema.job_split.JobSplit objects
    items = [
        JobSplit(
            id=item.id,
            job_id=item.job_id,
            index=item.index,
            video=item.video,
            images=item.images,
            selected=item.selected,
            start=item.start,
            end=item.end,
            text=item.text,
            prompt=item.prompt,

        )
        for item in result["items"]
    ]
    return {"total": result["total"], "items": items}


@job_split_router.put("/{job_id}", response_model=JobSplit, summary="更新任务片段")
def update_job_split(
    job_id: int = Path(..., ge=1),
    request: UpdateJobSplitRequest = Body(...),
    db: Session = Depends(get_db)
) -> JobSplit:
    """
    更新任务片段
    """
    service = JobSplitService(db)
    job_split = service.update_job_splits(job_id, request)
    return JobSplit(
        id=job_split.id,
        job_id=job_split.job_id,
        index=job_split.index,
        video=job_split.video,
        images=job_split.images,
        selected=job_split.selected,
        start=job_split.start,
        end=job_split.end,
        text=job_split.text,
        prompt=job_split.prompt,
    )