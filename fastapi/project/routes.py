# routes.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/foo")
async def foo():
    return "foo"

@router.get("/bar")
async def get_item_by_id(item_id: int):
    return "bar"

