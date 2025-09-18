from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reviews import Review as ReviewModel
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.routers.products import update_product_rating
from app.auth import get_current_buyer, get_current_admin
from app.db_depends import get_async_db


router = APIRouter(
    prefix='/reviews',
    tags=['reviews'],
)


@router.get('/', response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов.
    """
    stmt = await db.scalars(select(ReviewModel).where(ReviewModel.is_active == True))
    reviews = stmt.all()

    return reviews


@router.get('/{review_id}', response_model=ReviewSchema, status_code=status.HTTP_200_OK)
async def get_review(review_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию об отзыве по его ID.
    """
    stmt = await db.scalars(select(ReviewModel).where(ReviewModel.id == review_id,
                                                      ReviewModel.is_active == True))
    review = stmt.all()
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Review not found!'
        )

    return review


@router.post('/', response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(
        review: ReviewCreate,
        current_user: UserModel = Depends(get_current_buyer),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Создаёт новый отзыв для указанного товара. После добавления отзыва пересчитывает средний рейтинг товара.
    """
    product_stmt = await db.scalars(select(ProductModel).where(ProductModel.id == review.product_id,
                                                               ProductModel.is_active == True))
    product = product_stmt.first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found or inactive!'
        )

    if not 1 <= review.grade <= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Grade should be from 1 to 5!'
        )

    db_review = ReviewModel(**review.model_dump(),
                            user_id=current_user.id)
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)

    await update_product_rating(product.id, db)

    return db_review


@router.delete('/{review_id}', status_code=status.HTTP_200_OK)
async def delete_review(
        review_id: int,
        current_user: UserModel = Depends(get_current_admin),
        db: AsyncSession = Depends(get_async_db)
):
    review_stmt = await db.scalars(select(ReviewModel).where(ReviewModel.id == review_id,
                                                             ReviewModel.is_active == True))
    review = review_stmt.first()
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Review not found or inactive!'
        )

    await db.execute(
        update(ReviewModel)
        .where(ReviewModel.id == review_id)
        .values(is_active=False)
    )
    await db.commit()

    await update_product_rating(review.product_id, db)

    return {'message': 'Review deleted!'}