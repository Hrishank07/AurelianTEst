from typing import Any, AsyncGenerator, Optional
import uuid
import json, models

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from database import SessionLocal
import schemas

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai_client = OpenAI(api_key="[ENCRYPTION_KEY]")

SYSTEM_TEMPLATE = """"""

# Get a DB Session
async def get_db() -> AsyncGenerator:
    async with SessionLocal() as session:
        yield session


@app.get("/")
async def root():
    return {"message": "Hello World"}

# response_model represents the format of the response that this endpoint will produce. Responses are always in JSON
@app.get("/chat", response_model=list[schemas.Chat])
async def get_chats(db: AsyncSession = Depends(get_db)):
    chats = await crud.chat.get_multi(db, limit=10)
    return chats

# the data parameter represents the body of the request. The request body should always be in JSON format
@app.post("/chat", response_model=schemas.Chat)
async def create_chat(data: schemas.ChatCreate, db: AsyncSession = Depends(get_db)):
    chat = await crud.chat.create(db=db, obj_in=data)
    return chat

# the chat_id parameter maps to the chat id in the URL
@app.put("/chat/{chat_id}", response_model=schemas.Chat)
async def update_chat(
    chat_id: str, data: schemas.ChatUpdate, db: AsyncSession = Depends(get_db)
):
    chat = await crud.chat.get(db, id=chat_id)

    resp = openai_client.chat.completions.create(
        messages=[{"role": "system", "content": SYSTEM_TEMPLATE}] + data.messages,
        model="gpt-4o-mini",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "update_interest_form",
                    "description": "Update an existing interest form",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "form_id": {"type": "string"},
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "phone_number": {"type": "string"},
                            "status": {"type": "integer", "enum": [1, 2, 3]}
                        },
                        "required": ["form_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_interest_form",
                    "description": "Delete an interest form",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "form_id": {"type": "string"}
                        },
                        "required": ["form_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "submit_interest_form",
                    "description": "Submit an interest form for the user with the given properties",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "the user's name",
                            },
                            "email": {
                                "type": "string",
                                "description": "the user's email address",
                            },
                            "phone_number": {
                                "type": "string",
                                "description": "the user's phone number",
                            },
                        },
                    },
                },
            }
        ],
    )
    resp_message = resp.choices[0].message.model_dump()

    data.messages.append(resp_message)

    if resp_message.get('tool_calls'):
        for t in resp_message["tool_calls"]:
            
            #Task 1
            fname = t["function"]["name"]
            args = json.loads(t["function"]["arguments"])
            
            if fname == "submit_interest_form":
                form_data = schemas.FormSubmissionCreate(
                    name=args["name"], email=args["email"],
                    phone_number=args["phone_number"], chat_id=chat_id
                )
                await crud.form.create(db=db, obj_in=form_data)
            elif fname == "update_interest_form":
                fid = args.pop("form_id")
                f_obj = await crud.form.get(db, id=fid)
                if f_obj:
                    await crud.form.update(db, db_obj=f_obj, obj_in=args)
            elif fname == "delete_interest_form":
                await crud.form.remove(db, id=args["form_id"])

                
            data.messages.append(
                {
                    "tool_call_id": t["id"],
                    "role": "tool",
                    "name": t["function"]["name"],
                    "content": "Success",
                }
            )

        resp = openai_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_TEMPLATE}] + data.messages,
            model="gpt-4o-mini",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "update_interest_form",
                        "description": "Update an existing interest form",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "form_id": {"type": "string"},
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "phone_number": {"type": "string"},
                                "status": {"type": "integer", "enum": [1, 2, 3]}
                            },
                            "required": ["form_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "delete_interest_form",
                        "description": "Delete an interest form",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "form_id": {"type": "string"}
                            },
                            "required": ["form_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "submit_interest_form",
                        "description": "Submit an interest form for the user with the given properties",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "the user's name",
                                },
                                "email": {
                                    "type": "string",
                                    "description": "the user's email address",
                                },
                                "phone_number": {
                                    "type": "string",
                                    "description": "the user's phone number",
                                },
                            },
                        },
                    },
                }
            ],
        )
        resp_message = resp.choices[0].message.model_dump()

        data.messages.append(resp_message)

    chat = await crud.chat.update(db, db_obj=chat, obj_in=data)

    return chat


@app.get("/chat/{chat_id}", response_model=schemas.Chat)
async def get_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    chat = await crud.chat.get(db, id=chat_id)
    if not chat:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


#for get all form submissions for specific chat

@app.get("/chat/{chat_id}/forms", response_model=list[schemas.FormSubmission])
async def get_forms(chat_id: str, status: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    filters = [models.FormSubmission.chat_id == chat_id]
    if status is not None:
        filters.append(models.FormSubmission.status == status)
    
    forms = await crud.form.get_multi(db, filters=filters)
    return forms

    
@app.put("/form-submission/{form_id}", response_model=schemas.FormSubmission)
async def update_form(form_id: str, data: schemas.FormSubmissionUpdate, db: AsyncSession = Depends(get_db)):
    form_obj = await crud.form.get(db, id=form_id)
    if not form_obj:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Form not found")
    
    if data.status is not None and data.status not in [1, 2, 3]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Status must be 1 (TO DO), 2 (IN PROGRESS), or 3 (COMPLETED)")
        
    return await crud.form.update(db, db_obj=form_obj, obj_in=data)


@app.delete("/form-submission/{form_id}")
async def delete_form(form_id: str, db: AsyncSession = Depends(get_db)):
    await crud.form.remove(db, id=form_id)
    return {"message": "Deleted"}
    