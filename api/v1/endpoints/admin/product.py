from datetime import datetime
import json
from typing import Dict, List, Optional
from psycopg2 import IntegrityError
from slugify import slugify

from utils.file_uploads import get_media_url, save_uploaded_file
# from core.upload_files_to_space import upload_file_to_s3
from sqlalchemy.orm import selectinload
from utils.id_generators import generate_lowercase
from schemas.products import ProductResponse, ProductListResponse
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from core.status_codes import APIResponse, StatusCode
from db.models.superadmin import Category, SubCategory, Product, VendorLogin
from db.sessions.database import get_db
from sqlalchemy.future import select
from sqlalchemy import func

UPLOAD_CATEGORY_FOLDER = "uploads/products"



router = APIRouter()


@router.post("/create-product/", response_model=ProductResponse, status_code=201)
async def create_product(
    vendor_id: str = Form(...),
    cat_id: str = Form(...),
    subcat_id: Optional[str] = Form(default=None),
    identification: str = Form(...),
    descriptions: Optional[str] = Form(default=""),
    pricing: Optional[str] = Form(default=""),
    inventory: Optional[str] = Form(default=""),
    physical_attributes: Optional[str] = Form(default=""),
    files: List[UploadFile] = File(default=None),
    tags_and_relationships: Optional[str] = Form(default=""),
    status_flags: Optional[str] = Form(default=""),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Validate vendor
        result = await db.execute(select(VendorLogin).filter(VendorLogin.user_id == vendor_id))
        vendor_check = result.scalars().first()
        if not vendor_check:
            return APIResponse.response(StatusCode.NOT_FOUND, "Vendor not found", log_error=True)

        # Validate category
        result = await db.execute(select(Category).filter(Category.category_id == cat_id))
        category = result.scalars().first()
        if not category:
            return APIResponse.response(StatusCode.NOT_FOUND, "Category not found", log_error=True)

        # Validate subcategory
        subcategory = None
        if subcat_id:
            result = await db.execute(
                select(SubCategory).filter(
                    SubCategory.subcategory_id == subcat_id,
                    SubCategory.category_id == cat_id
                )
            )
            subcategory = result.scalars().first()
            if not subcategory:
                return APIResponse.response(
                    StatusCode.NOT_FOUND,
                    "Subcategory not found or does not belong to the selected category",
                    log_error=True
                )

        # Parse JSON fields
        try:
            identification_data = json.loads(identification)
            descriptions_data = json.loads(descriptions) if descriptions else {}
            pricing_data = json.loads(pricing) if pricing else {}
            inventory_data = json.loads(inventory) if inventory else {}
            physical_attributes_data = json.loads(physical_attributes) if physical_attributes else {}
            tags_and_relationships_data = json.loads(tags_and_relationships) if tags_and_relationships else {}
            status_flags_data = json.loads(status_flags) if status_flags else {}
        except json.JSONDecodeError as e:
            return APIResponse.response(StatusCode.BAD_REQUEST, f"Invalid JSON data: {str(e)}", log_error=True)

        # Validate product name
        product_name = identification_data.get("product_name", "").strip()
        if not product_name:
            return APIResponse.response(StatusCode.BAD_REQUEST, "Product name is required", log_error=True)

        # Generate unique slug
        base_slug = slugify(product_name)
        slug = base_slug
        suffix = 0
        while True:
            result = await db.execute(select(Product).filter(Product.slug == slug))
            if not result.scalars().first():
                break
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        # Generate product_id
        product_id = generate_lowercase(6)

        # Save uploaded images
        image_urls = []
        if files:
            for file in files:
                sub_path = f"products/{cat_id}/{slug}"
                uploaded_url = await save_uploaded_file(file, sub_path)
                if uploaded_url:
                    image_urls.append(uploaded_url)

        # Create product
        db_product = Product(
            product_id=product_id,
            vendor_id=vendor_id,
            category_id=cat_id,
            subcategory_id=subcat_id if subcat_id else None,
            identification={
                "product_name": product_name,
                "product_sku": identification_data.get("product_sku", "")
            },
            descriptions={
                "short_description": descriptions_data.get("short_description", ""),
                "full_description": descriptions_data.get("full_description", "")
            } if descriptions_data else None,
            pricing={
                "actual_price": pricing_data.get("actual_price", ""),
                "selling_price": pricing_data.get("selling_price", "")
            } if pricing_data else None,
            inventory={
                "quantity": inventory_data.get("stock_quantity", ""),
                "stock_alert_status": inventory_data.get("stock_alert_status", "instock")
            } if inventory_data else None,
            physical_attributes={
                "weight": physical_attributes_data.get("weight", ""),
                "dimensions": physical_attributes_data.get("dimensions", {}),
                "shipping_class": physical_attributes_data.get("shipping_class", "standard")
            } if physical_attributes_data else None,
            images={"urls": image_urls} if image_urls else None,
            tags_and_relationships={
                "product_tags": tags_and_relationships_data.get("product_tags", []),
                "linkedproductid": tags_and_relationships_data.get("linkedproductid", "")
            } if tags_and_relationships_data else None,
            status_flags={
                "featured_product": status_flags_data.get("featured_product", False),
                "published_product": status_flags_data.get("published_product", True),
                "product_status": status_flags_data.get("product_status", False)
            } if status_flags_data else {
                "featured_product": False,
                "published_product": True,
                "product_status": False
            },
            slug=slug
        )

        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)

        # Prepare response
        category_name = category.category_name
        subcategory_name = subcategory.subcategory_name if subcategory else None

        response_data = ProductResponse(
            product_id=db_product.product_id,
            vendor_id=db_product.vendor_id,
            slug=db_product.slug,
            identification=db_product.identification,
            descriptions=db_product.descriptions,
            pricing=db_product.pricing,
            inventory=db_product.inventory,
            physical_attributes=db_product.physical_attributes,
            images=db_product.images,
            tags_and_relationships=db_product.tags_and_relationships,
            status_flags=db_product.status_flags,
            timestamp=db_product.timestamp,
            category_id=db_product.category_id,
            category_name=category_name,
            subcategory_id=db_product.subcategory_id,
            subcategory_name=subcategory_name
        )

        return response_data

    except IntegrityError as e:
        await db.rollback()
        return APIResponse.response(StatusCode.BAD_REQUEST, f"Failed to create product: {str(e)}", log_error=True)
    except Exception as e:
        await db.rollback()
        return APIResponse.response(StatusCode.SERVER_ERROR, f"Unexpected error: {str(e)}", log_error=True)

@router.get("/", response_model=ProductListResponse, status_code=200)
async def get_all_products(db: AsyncSession = Depends(get_db)):
    try:
        # Get total count of products
        count_result = await db.execute(select(func.count(Product.product_id)))
        total_count = count_result.scalar()

        # Get all products with category and subcategory information
        result = await db.execute(select(Product).options(
            selectinload(Product.category),
            selectinload(Product.subcategory)
        ))
        products = result.scalars().all()

        if not products:
            return ProductListResponse(products=[], total_count=0)

        # Convert ORM objects to response-ready dicts
        product_responses = []
        for product in products:
            product_data = product.__dict__.copy()
            
            # Remove internal SQLAlchemy state
            product_data.pop("_sa_instance_state", None)

            product_data["category_id"] = product.category_id
            product_data["category_name"] = (
                product.category.category_name if product.category else None
            )
            product_data["subcategory_id"] = product.subcategory_id
            product_data["subcategory_name"] = (
                product.subcategory.subcategory_name if product.subcategory else None
            )

            product_responses.append(ProductResponse(**product_data))

        return ProductListResponse(products=product_responses, total_count=total_count)

    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR,
            f"Failed to retrieve products: {str(e)}",
            log_error=True,
        )

@router.get("/{product_id}", response_model=ProductResponse, status_code=200)
async def get_product_by_id(product_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Product).filter(Product.product_id == product_id))
        product = result.scalars().first()

        if not product:
            return APIResponse.response(
                StatusCode.NOT_FOUND,
                f"Product with ID {product_id} not found",
                log_error=False,
            )

        # Fetch category/subcategory names
        category_result = await db.execute(select(Category.category_name).where(Category.category_id == product.category_id))
        category_name = category_result.scalar()

        subcategory_result = await db.execute(select(SubCategory.subcategory_name).where(SubCategory.subcategory_id == product.subcategory_id))
        subcategory_name = subcategory_result.scalar()

        # Build and return ProductResponse
        product_response = ProductResponse(
            product_id=product.product_id,
            vendor_id=product.vendor_id,
            slug=product.slug,
            identification=product.identification,
            descriptions=product.descriptions,
            pricing=product.pricing,
            inventory=product.inventory,
            physical_attributes=product.physical_attributes,
            images=product.images,
            tags_and_relationships=product.tags_and_relationships,
            status_flags=product.status_flags,
            timestamp=product.timestamp,
            category_id=product.category_id,
            category_name=category_name,
            subcategory_id=product.subcategory_id,
            subcategory_name=subcategory_name,
        )
        return product_response

    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR,
            f"Failed to retrieve product: {str(e)}",
            log_error=True,
        )




@router.get("/slug/{slug}", response_model=ProductResponse, status_code=200)
async def get_product_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Product)
            .where(Product.slug == slug)
            .options(
                selectinload(Product.category),
                selectinload(Product.subcategory)
            )
        )
        product = result.scalars().first()

        if not product:
            return APIResponse.response(
                StatusCode.NOT_FOUND,
                f"Product with slug '{slug}' not found",
                log_error=False,
            )

        return ProductResponse(
            product_id=product.product_id,
            vendor_id=product.vendor_id,
            slug=product.slug,
            identification=product.identification,
            descriptions=product.descriptions,
            pricing=product.pricing,
            inventory=product.inventory,
            physical_attributes=product.physical_attributes,
            images=product.images,
            tags_and_relationships=product.tags_and_relationships,
            status_flags=product.status_flags,
            timestamp=product.timestamp,
            category_id=product.category_id,
            category_name=product.category.category_name if product.category else None,
            subcategory_id=product.subcategory_id,
            subcategory_name=product.subcategory.subcategory_name if product.subcategory else None,
        )

    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR,
            f"Failed to retrieve product by slug: {str(e)}",
            log_error=True,
        )


@router.get("/by-vendor/{vendor_id}", response_model=List[ProductResponse])
async def get_products_by_vendor_id(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.subcategory),
            )
            .filter(Product.vendor_id == vendor_id)
        )
        products = result.scalars().all()

        if not products:
            return APIResponse.response(
                StatusCode.NOT_FOUND,
                f"No products found for vendor ID {vendor_id}",
                log_error=False,
            )

        # Map products into the correct response model
        response = []
        for product in products:
            image_urls = []
            if product.images and "urls" in product.images:
                image_urls = [get_media_url(url) for url in product.images["urls"]]

            response.append(
                ProductResponse(
                    product_id=product.product_id,
                    vendor_id=product.vendor_id,
                    slug=product.slug,
                    identification=product.identification,
                    descriptions=product.descriptions,
                    pricing=product.pricing,
                    inventory=product.inventory,
                    physical_attributes=product.physical_attributes,
                    
                    tags_and_relationships=product.tags_and_relationships,
                    status_flags=product.status_flags,
                    images={"urls": image_urls} if image_urls else None,
                    timestamp=product.timestamp,
                    category_id=product.category_id,
                    category_name=product.category.category_name if product.category else None,
                    subcategory_id=product.subcategory_id,
                    subcategory_name=product.subcategory.subcategory_name if product.subcategory else None,
                )
            )

        return response

    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR,
            f"Failed to retrieve products: {str(e)}",
            log_error=True,
        )



@router.put("/{product_id}", response_model=ProductResponse, status_code=200)
async def update_product(
    product_id: str,
    cat_id: Optional[str] = Form(default=None),
    subcat_id: Optional[str] = Form(default=None),
    identification: Optional[str] = Form(default=None),
    descriptions: Optional[str] = Form(default=None),
    pricing: Optional[str] = Form(default=None),
    inventory: Optional[str] = Form(default=None),
    physical_attributes: Optional[str] = Form(default=None),
    files: List[UploadFile] = File(default=None),
    tags_and_relationships: Optional[str] = Form(default=None),
    status_flags: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Product).filter(Product.product_id == product_id))
    product = result.scalars().first()

    if not product:
        return APIResponse.response(
            StatusCode.NOT_FOUND,
            f"Product with ID {product_id} not found",
            log_error=True,
        )

    if cat_id:
        result = await db.execute(select(Category).filter(Category.category_id == cat_id))
        if not result.scalars().first():
            return APIResponse.response(StatusCode.NOT_FOUND, "Category not found", log_error=True)
        product.category_id = cat_id

    if subcat_id:
        result = await db.execute(select(SubCategory).filter(SubCategory.subcategory_id == subcat_id))
        if not result.scalars().first():
            return APIResponse.response(StatusCode.NOT_FOUND, "Subcategory not found", log_error=True)
        product.subcategory_id = subcat_id

    try:
        if identification is not None:
            product.identification = {**product.identification, **json.loads(identification)}

        if descriptions is not None:
            desc_data = json.loads(descriptions)
            product.descriptions = {**(product.descriptions or {}), **desc_data}

        if pricing is not None:
            price_data = json.loads(pricing)
            product.pricing = {**(product.pricing or {}), **price_data}

        if inventory is not None:
            inv_data = json.loads(inventory)
            product.inventory = {**(product.inventory or {}), **inv_data}

        if physical_attributes is not None:
            phys_data = json.loads(physical_attributes)
            product.physical_attributes = {**(product.physical_attributes or {}), **phys_data}

        if tags_and_relationships is not None:
            tag_data = json.loads(tags_and_relationships)
            product.tags_and_relationships = {**(product.tags_and_relationships or {}), **tag_data}

        if status_flags is not None:
            status_data = json.loads(status_flags)
            product.status_flags = {**product.status_flags, **status_data}
    except json.JSONDecodeError as e:
        return APIResponse.response(StatusCode.BAD_REQUEST, f"Invalid JSON data: {str(e)}", log_error=True)

    if files:
        try:
            image_urls = []
            product_name = product.identification.get("product_name", "").replace(" ", "_").lower()
            cleaned_product_id = product_id.replace(" ", "_").lower()

            for file in files:
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                new_filename = f"{timestamp}_{file.filename}"
                file_path = f"products/{product_name}/{cleaned_product_id}/{new_filename}"
                # image_url = await upload_file_to_s3(file, file_path)
                # image_urls.append(image_url)

            product.images = {"urls": image_urls}
        except Exception as e:
            return APIResponse.response(StatusCode.SERVER_ERROR, f"Failed to upload images: {str(e)}", log_error=True)

    await db.commit()
    await db.refresh(product)

    # Fetch category and subcategory names
    category_name = None
    subcategory_name = None

    if product.category_id:
        result = await db.execute(
            select(Category.category_name).filter(Category.category_id == product.category_id)
        )
        category_name = result.scalar()

    if product.subcategory_id:
        result = await db.execute(
            select(SubCategory.subcategory_name).filter(SubCategory.subcategory_id == product.subcategory_id)
        )
        subcategory_name = result.scalar()

    return ProductResponse(
        product_id=product.product_id,
        vendor_id=product.vendor_id,
        slug=product.slug,
        identification=product.identification,
        descriptions=product.descriptions,
        pricing=product.pricing,
        inventory=product.inventory,
        physical_attributes=product.physical_attributes,
        images=product.images,
        tags_and_relationships=product.tags_and_relationships,
        status_flags=product.status_flags,
        timestamp=product.timestamp,
        category_id=product.category_id,
        category_name=category_name,
        subcategory_id=product.subcategory_id,
        subcategory_name=subcategory_name
    )


@router.put("/{slug}", response_model=ProductResponse, status_code=200)
async def update_product_by_slug(
    slug: str,
    cat_id: Optional[str] = Form(default=None),
    subcat_id: Optional[str] = Form(default=None),
    identification: Optional[str] = Form(default=None),
    descriptions: Optional[str] = Form(default=None),
    pricing: Optional[str] = Form(default=None),
    inventory: Optional[str] = Form(default=None),
    physical_attributes: Optional[str] = Form(default=None),
    files: List[UploadFile] = File(default=None),
    tags_and_relationships: Optional[str] = Form(default=None),
    status_flags: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Product).filter(Product.slug == slug))
    product = result.scalars().first()

    if not product:
        return APIResponse.response(
            StatusCode.NOT_FOUND,
            f"Product with slug '{slug}' not found",
            log_error=True,
        )

    if cat_id:
        result = await db.execute(select(Category).filter(Category.category_id == cat_id))
        if not result.scalars().first():
            return APIResponse.response(StatusCode.NOT_FOUND, "Category not found", log_error=True)
        product.category_id = cat_id

    if subcat_id:
        result = await db.execute(select(SubCategory).filter(SubCategory.subcategory_id == subcat_id))
        if not result.scalars().first():
            return APIResponse.response(StatusCode.NOT_FOUND, "Subcategory not found", log_error=True)
        product.subcategory_id = subcat_id

    try:
        if identification is not None:
            product.identification = {**product.identification, **json.loads(identification)}

        if descriptions is not None:
            desc_data = json.loads(descriptions)
            product.descriptions = {**(product.descriptions or {}), **desc_data}

        if pricing is not None:
            price_data = json.loads(pricing)
            product.pricing = {**(product.pricing or {}), **price_data}

        if inventory is not None:
            inv_data = json.loads(inventory)
            product.inventory = {**(product.inventory or {}), **inv_data}

        if physical_attributes is not None:
            phys_data = json.loads(physical_attributes)
            product.physical_attributes = {**(product.physical_attributes or {}), **phys_data}

        if tags_and_relationships is not None:
            tag_data = json.loads(tags_and_relationships)
            product.tags_and_relationships = {**(product.tags_and_relationships or {}), **tag_data}

        if status_flags is not None:
            status_data = json.loads(status_flags)
            product.status_flags = {**product.status_flags, **status_data}
    except json.JSONDecodeError as e:
        return APIResponse.response(StatusCode.BAD_REQUEST, f"Invalid JSON data: {str(e)}", log_error=True)

    if files:
        try:
            image_urls = []
            product_name = product.identification.get("product_name", "").replace(" ", "_").lower()
            cleaned_slug = slug.replace(" ", "_").lower()

            for file in files:
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                new_filename = f"{timestamp}_{file.filename}"
                file_path = f"products/{product_name}/{cleaned_slug}/{new_filename}"
                # image_url = await upload_file_to_s3(file, file_path)
                # image_urls.append(image_url)

            product.images = {"urls": image_urls}
        except Exception as e:
            return APIResponse.response(StatusCode.SERVER_ERROR, f"Failed to upload images: {str(e)}", log_error=True)

    await db.commit()
    await db.refresh(product)

    # Fetch category and subcategory names
    category_name = None
    subcategory_name = None

    if product.category_id:
        result = await db.execute(
            select(Category.category_name).filter(Category.category_id == product.category_id)
        )
        category_name = result.scalar()

    if product.subcategory_id:
        result = await db.execute(
            select(SubCategory.subcategory_name).filter(SubCategory.subcategory_id == product.subcategory_id)
        )
        subcategory_name = result.scalar()

    return ProductResponse(
        product_id=product.product_id,
        vendor_id=product.vendor_id,
        slug=product.slug,
        identification=product.identification,
        descriptions=product.descriptions,
        pricing=product.pricing,
        inventory=product.inventory,
        physical_attributes=product.physical_attributes,
        images=product.images,
        tags_and_relationships=product.tags_and_relationships,
        status_flags=product.status_flags,
        timestamp=product.timestamp,
        category_id=product.category_id,
        category_name=category_name,
        subcategory_id=product.subcategory_id,
        subcategory_name=subcategory_name
    )


@router.put("/slug/{slug}/delete", response_model=Dict)
async def soft_delete_product_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.slug == slug))
    product = result.scalars().first()

    if not product:
        return APIResponse.response(
            StatusCode.NOT_FOUND,
            f"Product with slug '{slug}' not found",
            log_error=True
        )

    product.status_flags["product_status"] = True
    await db.commit()

    return {"message": f"Product with slug '{slug}' soft deleted successfully"}



@router.put("/{product_id}/delete", response_model=Dict)
async def soft_delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.product_id == product_id))
    product = result.scalars().first()

    if not product:
        return APIResponse.response(
            StatusCode.NOT_FOUND,
            f"Product with ID {product_id} not found",
            log_error=True
        )

    product.status_flags["product_status"] = True
    await db.commit()

    return {"message": f"Product {product_id} soft deleted successfully"}


@router.put("/{product_id}/restore", response_model=Dict)
async def restore_product(product_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.product_id == product_id))
    product = result.scalars().first()

    if not product:
        return APIResponse.response(
            StatusCode.NOT_FOUND,
            f"Product with ID {product_id} not found",
            log_error=True
        )

    product.status_flags["product_status"] = False
    await db.commit()

    return {"message": f"Product {product_id} restored successfully"}


@router.put("/slug/{slug}/restore", response_model=Dict)
async def restore_product(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.slug == slug))
    product = result.scalars().first()

    if not product:
        return APIResponse.response(
            StatusCode.NOT_FOUND,
            f"Product with slug {slug} not found",
            log_error=True
        )

    product.status_flags["product_status"] = False
    await db.commit()

    return {"message": f"Product {slug} restored successfully"}