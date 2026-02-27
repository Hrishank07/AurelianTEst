from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import crud
import models
import schemas
from database import SessionLocal

router = APIRouter()

# Dependency
async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/chat/{chat_id}/forms", response_model=List[schemas.FormSubmission])
async def get_forms(
    chat_id: str, 
    status: Optional[int] = None, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get all form submissions for a specific chat.
    Supports filtering by status (1, 2, or 3).
    """
    filters = [models.FormSubmission.chat_id == chat_id]
    if status is not None:
        if status not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="Invalid status filter. Use 1 (TO DO), 2 (IN PROGRESS), or 3 (COMPLETED)")
        filters.append(models.FormSubmission.status == status)
    
    forms = await crud.form.get_multi(db, filters=filters)
    return forms

@router.put("/form-submission/{form_id}", response_model=schemas.FormSubmission)
async def update_form(
    form_id: str, 
    data: schemas.FormSubmissionUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update a form submission. 
    Validates that status is either None, 1, 2, or 3.
    """
    form_obj = await crud.form.get(db, id=form_id)
    if not form_obj:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    if data.status is not None and data.status not in [1, 2, 3]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid status. Must be 1 (TO DO), 2 (IN PROGRESS), or 3 (COMPLETED)"
        )

    updated_form = await crud.form.update(db, db_obj=form_obj, obj_in=data)
    return updated_form

@router.delete("/form-submission/{form_id}")
async def delete_form(form_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a form submission.
    """
    form_obj = await crud.form.get(db, id=form_id)
    if not form_obj:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    await crud.form.remove(db, id=form_id)
    return {"message": "Form submission deleted successfully"}
