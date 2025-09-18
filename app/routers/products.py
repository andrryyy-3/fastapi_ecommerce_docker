from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.models.reviews import Review as ReviewModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.auth import get_current_seller
from app.db_depends import get_async_db


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema], status_code=status.HTTP_200_OK)
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    stmt = await db.scalars(select(ProductModel).where(ProductModel.is_active == True))
    products = stmt.all()

    return products


@router.get("/category/{category_id}", response_model=list[ProductSchema], status_code=status.HTTP_200_OK)
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    category_stmt = await db.scalars(select(CategoryModel).where(CategoryModel.id == category_id,
                                                                 CategoryModel.is_active == True))
    category = category_stmt.first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category not found or inactive!'
        )

    stmt = await db.scalars(select(ProductModel).where(ProductModel.category_id == category_id,
                                                       ProductModel.is_active == True))
    products = stmt.all()

    return products


@router.get("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt = await db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                       ProductModel.is_active == True))
    product = stmt.first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found or inactive!'
        )

    category_stmt = await db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id,
                                                                 CategoryModel.is_active == True))
    category = category_stmt.first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category not found'
        )

    return product


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductCreate,
        current_user: UserModel = Depends(get_current_seller),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """
    stmt = await db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id,
                                       CategoryModel.is_active == True))
    db_category_id = stmt.first()
    if db_category_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category not found or inactive!'
        )

    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return db_product


@router.put("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def update_product(
        product_id: int,
        product: ProductCreate,
        current_user: UserModel = Depends(get_current_seller),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет товар, если он принадлежит текущему продавцу (только для 'seller').
    """
    stmt = await db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                 ProductModel.is_active == True))
    db_product = stmt.first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found!'
        )

    if db_product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You can only update your own products!'
        )

    category_stmt = await db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id,
                                                                 CategoryModel.is_active == True))
    db_category = category_stmt.first()
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category not found or inactive'
        )

    await db.execute(
          update(ProductModel)
          .where(ProductModel.id == product_id)
          .values(**product.model_dump())
    )
    await db.commit()
    await db.refresh(db_product)

    return db_product


@router.delete("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def delete_product(
        product_id: int,
        current_user: UserModel = Depends(get_current_seller),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """
    stmt = await db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                       ProductModel.is_active == True))
    product = stmt.first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found or inactive!'
        )

    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You can only delete your own products!'
        )

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(is_active=False)
    )
    await db.commit()
    await db.refresh(product)

    return product


async def update_product_rating(product_id: int, db: AsyncSession = Depends(get_async_db)):
    stmt_updated_rating = select(func.avg(ReviewModel.grade)).where(ReviewModel.product_id == product_id,
                                                                    ReviewModel.is_active == True)
    updated_rating = await db.scalar(stmt_updated_rating)
    if updated_rating is None:
        updated_rating = 0.0

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(rating=updated_rating)
    )
    await db.commit()

    return
