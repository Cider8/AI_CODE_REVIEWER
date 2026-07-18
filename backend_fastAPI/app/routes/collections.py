from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId

from app.models.user import User
from app.models.collection import Collection
from app.models.review import Review
from app.dependencies import get_current_user
from app.utils.convert import doc_to_schema
from app.schemas.stats_schema import (
    CreateCollectionRequest,
    AddReviewRequest,
    CollectionOut,
)
from app.schemas.review_schema import ReviewListItem

router = APIRouter(prefix="/api/collections", tags=["collections"])


async def _to_collection_out(col: Collection) -> CollectionOut:
    """Manually populate review_ids -> ReviewListItem (Beanie has no
    auto-populate like Mongoose's .populate())."""
    reviews: list[ReviewListItem] = []
    if col.review_ids:
        docs = await Review.find({"_id": {"$in": col.review_ids}}).to_list()
        reviews = [doc_to_schema(d, ReviewListItem) for d in docs]

    data = col.model_dump()
    data.pop("id", None)
    data["_id"] = col.id
    data["review_ids"] = reviews
    return CollectionOut(**data)


# POST /api/collections
@router.post("", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CreateCollectionRequest,
    current_user: User = Depends(get_current_user),
):
    col = Collection(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
    )
    await col.insert()
    return await _to_collection_out(col)


# GET /api/collections
@router.get("", response_model=list[CollectionOut])
async def list_collections(current_user: User = Depends(get_current_user)):
    cols = await Collection.find(Collection.user_id == current_user.id).to_list()
    return [await _to_collection_out(c) for c in cols]


# PATCH /api/collections/{id}/add-review
@router.patch("/{collection_id}/add-review", response_model=CollectionOut)
async def add_review_to_collection(
    collection_id: PydanticObjectId,
    body: AddReviewRequest,
    current_user: User = Depends(get_current_user),
):
    col = await Collection.find_one(
        Collection.id == collection_id,
        Collection.user_id == current_user.id,
    )
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    if body.review_id not in col.review_ids:
        col.review_ids.append(body.review_id)
        await col.save()

    return await _to_collection_out(col)


# DELETE /api/collections/{id}
@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: PydanticObjectId,
    current_user: User = Depends(get_current_user),
):
    col = await Collection.find_one(
        Collection.id == collection_id,
        Collection.user_id == current_user.id,
    )
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    await col.delete()
    return {"message": "Collection deleted"}
