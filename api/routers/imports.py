from fastapi import APIRouter, Depends
from auth.authenticate import authenticate
from fastapi import HTTPException, Query
from pydantic import BaseModel
