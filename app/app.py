from bson import ObjectId 
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from pydantic import BaseModel, BeforeValidator, Field
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Annotated
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017") # Default to local MongoDB

PyObjectID = Annotated[str, BeforeValidator(str)]

class Person(BaseModel):
    id: PyObjectID | None = Field(default=None, alias="_id")
    name: str
    occupation: str
    address: str

class PersonCollection(BaseModel):
    persons: list[Person]     

app = FastAPI()

connection = AsyncIOMotorClient(MONGO_URI)
db = connection.get_database("people")

@app.get("/")
async def root():
    return {"message": "I am working fine!"}

@app.post("/person")
async def create_person(person_req: Person):
    person_dict = person_req.model_dump()
    inserted_person = await db["people"].insert_one(person_dict)
    
    person = await db["people"].find_one({"_id": inserted_person.inserted_id})
    return Person(**person)

@app.get("/persons")
async def get_persons():
    person_collection = await db["people"].find().to_list(length=100)
    return PersonCollection(persons=person_collection)

@app.get("/persons/{person_id}")
async def get_person(person_id: PyObjectID):
    try:
        person = await db["people"].find_one({"_id": ObjectId(person_id)})
        if not person:
            raise HTTPException(detail={"message": "Person not found"}, status_code=404)
        return Person(**person)
    except:
        raise HTTPException(detail={f"message": "Person not found"}, status_code=404)
    
@app.delete("/persons/{person_id}")
async def delete_person(person_id: PyObjectID):
    await get_person(person_id) # Throws error if person not found
    
    await db["people"].delete_one({"_id": ObjectId(person_id)})
    return Response(status_code=204)

class PersonUpdate(BaseModel):
    name: str | None = None
    occupation: str | None = None
    address: str | None = None

@app.patch("/persons/{person_id}")
async def update_person(person_id: PyObjectID, person_req: PersonUpdate):
    person_id = ObjectId(person_id) # Convert to bson ObjectId for MongoDB query
    await get_person(person_id)

    person_update = {k: v for k, v in person_req.model_dump().items() if v is not None}
    try: 
        coll = db.people
        await coll.update_one({"_id": person_id}, {"$set": person_update})
        person = await coll.find_one({"_id": person_id})
        return Person(**person)
    except:
        raise HTTPException(detail={"message": "Update failed"}, status_code=404)