import csv
from datetime import datetime
import io
import json
import os
from typing import Dict, List, Optional
import aiofiles
from psycopg2 import IntegrityError
from slugify import slugify

from utils.file_uploads import get_media_url, save_uploaded_file
from utils.upload_files import upload_file_to_s3
from sqlalchemy.orm import selectinload
from utils.id_generators import generate_lowercase
from schemas.products import ProductByCategoryListResponse, ProductByCategoryResponse, ProductResponse, ProductListResponse, ProductSearchListResponse, ProductSearchResponse, VendorProductsResponse
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.status_codes import APIResponse, StatusCode
from db.models.superadmin import Category, SubCategory, Product, VendorLogin, BusinessProfile
from db.sessions.database import get_db
from sqlalchemy.future import select
from sqlalchemy import func

UPLOAD_CATEGORY_FOLDER = "uploads/products"


def safe_json_parse(json_str: Optional[str]) -> Optional[dict]:
    """Safely parse JSON string, returning None if string is None or empty"""
    if json_str is None or not json_str.strip():
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        raise


async def generate_unique_slug(product_name: str, db: AsyncSession, current_product_id: str = None) -> str:
    """Generate a unique slug from product name, excluding current product if updating"""
    base_slug = slugify(product_name)
    slug = base_slug
    suffix = 0
    while True:
        query = select(Product).filter(Product.slug == slug)
        if current_product_id:
            query = query.filter(Product.product_id != current_product_id)
        result = await db.execute(query)
        if not result.scalars().first():
            break
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    return slug


router = APIRouter()



@router.post("/bulk-upload-products/")
async def bulk_upload_products(
    file: UploadFile = File(...),
    vendor_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Validate vendor
        result = await db.execute(
            select(VendorLogin)
            .options(selectinload(VendorLogin.business_profile))
            .filter(VendorLogin.user_id == vendor_id)
        )
        vendor_check = result.scalars().first()
        if not vendor_check or vendor_check.username != "unknown":
            return APIResponse.response(StatusCode.NOT_FOUND, "Vendor not found", log_error=True)

        # Read CSV
        content = await file.read()
        csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

        products_to_create = []
        failed_rows = []
        row_num = 1

        async for row in _iterate_csv(csv_reader):
            try:
                # Product basic info
                product_name = row.get("product_name", "").strip()
                if not product_name:
                    raise ValueError("Product name is required")

                category_name = row.get("category_name", "").strip()
                subcategory_name = row.get("subcategory_name", "").strip()  # optional

                # Resolve category_id
                result = await db.execute(select(Category).filter(Category.category_name == category_name))
                category = result.scalars().first()
                if not category:
                    raise ValueError(f"Category '{category_name}' not found")
                cat_id = category.category_id

                # Resolve subcategory_id (if provided)
                subcat_id = None
                if subcategory_name:
                    result = await db.execute(
                        select(SubCategory).filter(
                            SubCategory.subcategory_name == subcategory_name,
                            SubCategory.category_id == cat_id
                        )
                    )
                    subcategory = result.scalars().first()
                    if not subcategory:
                        raise ValueError(f"Subcategory '{subcategory_name}' not valid for category '{category_name}'")
                    subcat_id = subcategory.subcategory_id

                # Generate slug
                base_slug = slugify(product_name)
                slug = base_slug
                suffix = 0
                while True:
                    res = await db.execute(select(Product).filter(Product.slug == slug))
                    if not res.scalars().first():
                        break
                    suffix += 1
                    slug = f"{base_slug}-{suffix}"

                # Generate product_id
                product_id = generate_lowercase(6)

                # Handle images
                images = [img.strip() for img in row.get("images", "").split("|") if img.strip()]
                image_urls = []
                for img_path in images:
                    async with aiofiles.open(img_path, 'rb') as f:
                        file_bytes = await f.read()
                        filename = os.path.basename(img_path)
                        url = await upload_file_to_s3(file_bytes, file_path=f"products/{filename}")
                        image_urls.append(url)

                # Build product
                db_product = Product(
                    product_id=product_id,
                    vendor_id=vendor_id,
                    category_id=cat_id,
                    subcategory_id=subcat_id,
                    slug=slug,
                    identification={
                        "product_name": product_name,
                        "product_sku": row.get("product_sku", "").strip()
                    },
                    descriptions={
                        "short_description": row.get("short_description", "").strip(),
                        "full_description": row.get("full_description", "").strip()
                    },
                    pricing={
                        "actual_price": row.get("actual_price", "").strip(),
                        "selling_price": row.get("selling_price", "").strip()
                    },
                    inventory={
                        "quantity": row.get("stock_quantity", "").strip(),
                        "stock_alert_status": row.get("stock_alert_status", "instock").strip()
                    },
                    physical_attributes={
                        "weight": row.get("weight", "").strip(),
                        "dimensions": row.get("dimensions", "{}").strip(),
                        "shipping_class": row.get("shipping_class", "standard").strip()
                    },
                    images={"urls": image_urls},
                    tags_and_relationships={
                        "product_tags": [t.strip() for t in row.get("product_tags", "").split("|") if t.strip()],
                        "linkedproductid": row.get("linkedproductid", "").strip()
                    },
                    status_flags={
                        "featured_product": row.get("featured_product", "false").lower() == "true",
                        "published_product": row.get("published_product", "true").lower() == "true",
                        "product_status": row.get("product_status", "false").lower() == "true"
                    }
                )

                products_to_create.append(db_product)

            except Exception as e:
                failed_rows.append({"row": row_num, "error": str(e), "data": row})

            row_num += 1

        # Bulk insert
        if products_to_create:
            db.add_all(products_to_create)
            await db.commit()

        return {
            "success_count": len(products_to_create),
            "failed_count": len(failed_rows),
            "failed_rows": failed_rows
        }

    except IntegrityError as e:
        await db.rollback()
        return APIResponse.response(StatusCode.BAD_REQUEST, f"Integrity error: {str(e)}", log_error=True)
    except Exception as e:
        await db.rollback()
        return APIResponse.response(StatusCode.SERVER_ERROR, f"Unexpected error: {str(e)}", log_error=True)


async def _iterate_csv(reader):
    """Helper to simulate async loop over CSV"""
    for row in reader:
        yield row



# @router.post("/bulk-upload-products/")
# async def bulk_upload_products(
#     file: UploadFile = File(...),
#     vendor_id: str = Form(...),
#     db: AsyncSession = Depends(get_db)
# ):
#     try:
#         # Validate vendor
#         result = await db.execute(
#             select(VendorLogin)
#             .options(selectinload(VendorLogin.business_profile))
#             .filter(VendorLogin.user_id == vendor_id)
#         )
#         vendor_check = result.scalars().first()
#         if not vendor_check or vendor_check.username != "unknown":
#             return APIResponse.response(StatusCode.NOT_FOUND, "Vendor not found", log_error=True)

#         # Read CSV
#         content = await file.read()
#         csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

#         products_to_create = []
#         failed_rows = []
#         row_num = 1

#         async for row in _iterate_csv(csv_reader):  # custom async loop helper
#             try:
#                 product_name = row.get("product_name", "").strip()
#                 if not product_name:
#                     raise ValueError("Product name is required")

#                 cat_id = row.get("category_id")
#                 subcat_id = row.get("subcategory_id")

#                 # Validate category
#                 result = await db.execute(select(Category).filter(Category.category_id == cat_id))
#                 category = result.scalars().first()
#                 if not category:
#                     raise ValueError(f"Category {cat_id} not found")

#                 # Validate subcategory
#                 subcategory = None
#                 if subcat_id:
#                     result = await db.execute(
#                         select(SubCategory).filter(
#                             SubCategory.subcategory_id == subcat_id,
#                             SubCategory.category_id == cat_id
#                         )
#                     )
#                     subcategory = result.scalars().first()
#                     if not subcategory:
#                         raise ValueError(f"Subcategory {subcat_id} not valid for category {cat_id}")

#                 # Generate slug
#                 base_slug = slugify(product_name)
#                 slug = base_slug
#                 suffix = 0
#                 while True:
#                     res = await db.execute(select(Product).filter(Product.slug == slug))
#                     if not res.scalars().first():
#                         break
#                     suffix += 1
#                     slug = f"{base_slug}-{suffix}"

#                 # Generate product_id
#                 product_id = generate_lowercase(6)

#                 images = row.get("images", "").split("|")  # assuming multiple images separated by "|"
#                 image_urls = []

#                 for img_path in images:
#                     img_path = img_path.strip()  # remove leading/trailing spaces and newlines
#                     if not img_path:
#                         continue  # skip empty paths

#                     async with aiofiles.open(img_path, 'rb') as f:
#                         upload_file = UploadFile(filename=os.path.basename(img_path), file=f)
#                         url = await upload_file_to_s3(await f.read(), file_path=f"products/{os.path.basename(img_path)}")
#                         image_urls.append(url)


#                 # Build product
#                 db_product = Product(
#                     product_id=product_id,
#                     vendor_id=vendor_id,
#                     category_id=cat_id,
#                     subcategory_id=subcat_id if subcat_id else None,
#                     slug=slug,
#                     identification={
#                         "product_name": product_name,
#                         "product_sku": row.get("product_sku", "")
#                     },
#                     descriptions={
#                         "short_description": row.get("short_description", ""),
#                         "full_description": row.get("full_description", "")
#                     },
#                     pricing={
#                         "actual_price": row.get("actual_price", ""),
#                         "selling_price": row.get("selling_price", "")
#                     },
#                     inventory={
#                         "quantity": row.get("stock_quantity", ""),
#                         "stock_alert_status": row.get("stock_alert_status", "instock")
#                     },
#                     physical_attributes={
#                         "weight": row.get("weight", ""),
#                         "dimensions": row.get("dimensions", "{}"),
#                         "shipping_class": row.get("shipping_class", "standard")
#                     },
#                     images={"urls": image_urls},
#                     tags_and_relationships={
#                         "product_tags": row.get("product_tags", "").split("|"),
#                         "linkedproductid": row.get("linkedproductid", "")
#                     },
#                     status_flags={
#                         "featured_product": row.get("featured_product", "false").lower() == "true",
#                         "published_product": row.get("published_product", "true").lower() == "true",
#                         "product_status": row.get("product_status", "false").lower() == "true"
#                     }
#                 )

#                 products_to_create.append(db_product)

#             except Exception as e:
#                 failed_rows.append({"row": row_num, "error": str(e), "data": row})

#             row_num += 1

#         # Bulk insert
#         if products_to_create:
#             db.add_all(products_to_create)
#             await db.commit()

#         return {
#             "success_count": len(products_to_create),
#             "failed_count": len(failed_rows),
#             "failed_rows": failed_rows
#         }

#     except IntegrityError as e:
#         await db.rollback()
#         return APIResponse.response(StatusCode.BAD_REQUEST, f"Integrity error: {str(e)}", log_error=True)
#     except Exception as e:
#         await db.rollback()
#         return APIResponse.response(StatusCode.SERVER_ERROR, f"Unexpected error: {str(e)}", log_error=True)


# async def _iterate_csv(reader):
#     """Helper to simulate async loop over CSV"""
#     for row in reader:
#         yield row


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
        result = await db.execute(
            select(VendorLogin)
            .options(selectinload(VendorLogin.business_profile))
            .filter(VendorLogin.user_id == vendor_id)
        )
        vendor_check = result.scalars().first()
        if not vendor_check:
            return APIResponse.response(StatusCode.NOT_FOUND, "Vendor not found", log_error=True)
        
        # Check if username is "unknown" (vendor) vs vendor employee
        if vendor_check.username != "unknown":
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

        # Validate that at least one image is provided
        if not files or len(files) == 0:
            return APIResponse.response(StatusCode.BAD_REQUEST, "At least one product image is required", log_error=True)
        
        # Check if any file has content
        valid_files = [f for f in files if f and f.filename]
        if not valid_files:
            return APIResponse.response(StatusCode.BAD_REQUEST, "At least one valid product image is required", log_error=True)

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
        for file in valid_files:
            sub_path = f"products/{cat_id}/{slug}"
            uploaded_url = await save_uploaded_file(file, sub_path)
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
            images={"urls": image_urls},
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
        
        # Get store_name from business profile
        store_name = None
        if vendor_check and vendor_check.business_profile:
            store_name = vendor_check.business_profile.store_name

        response_data = ProductResponse(
            product_id=db_product.product_id,
            store_name=store_name,
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

        # Get all products with category, subcategory, and vendor business profile information
        result = await db.execute(
            select(Product, VendorLogin, BusinessProfile)
            .join(VendorLogin, Product.vendor_id == VendorLogin.user_id)
            .join(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
            .options(
                selectinload(Product.category),
                selectinload(Product.subcategory)
            )
        )
        products_data = result.all()

        if not products_data:
            return ProductListResponse(products=[], total_count=0)

        # Convert ORM objects to response-ready dicts
        product_responses = []
        for product, vendor_login, business_profile in products_data:
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
            
            # Add store_name from business profile
            product_data["store_name"] = business_profile.store_name if business_profile else None
            
            # Remove vendor_id from response
            product_data.pop("vendor_id", None)

            # Process image URLs
            if product.images and "urls" in product.images:
                image_urls = [get_media_url(url) for url in product.images["urls"]]
                product_data["images"] = {"urls": image_urls}

            product_responses.append(ProductResponse(**product_data))

        return ProductListResponse(products=product_responses, total_count=total_count)

    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR,
            f"Failed to retrieve products: {str(e)}",
            log_error=True,
        )

@router.get("/search", response_model=ProductSearchListResponse, status_code=200)
async def search_products(db: AsyncSession = Depends(get_db)):

    try:
        # Build the query to get 10 products
        query = (
            select(Product, Category.category_name.label("category_name"))
            .join(Category, Product.category_id == Category.category_id)
            .limit(10)
        )
        
        # Get total count of all products
        count_query = select(func.count(Product.product_id))
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Execute the main query
        result = await db.execute(query)
        products_data = result.all()
        
        # Format the response
        products = []
        for product, category_name in products_data:
            # Extract product image (first available image)
            product_image = None
            if product.images and "urls" in product.images and product.images["urls"]:
                product_image = get_media_url(product.images["urls"][0])
            
            # Extract pricing
            product_pricing = None
            if product.pricing and product.pricing.get("selling_price"):
                product_pricing = product.pricing["selling_price"]
            
            # Extract product name
            product_name = product.identification.get("product_name", "")
            
            products.append(ProductSearchResponse(
                product_id=product.product_id,
                product_name=product_name,
                product_image=product_image,
                product_pricing=product_pricing,
                slug=product.slug,
                category=category_name
            ))
        
        return ProductSearchListResponse(
            products=products,
            total_count=total_count
        )
        
    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR,
            f"Failed to search products: {str(e)}",
            log_error=True,
        )

@router.get("/search-by-name", response_model=ProductSearchListResponse, status_code=200)
async def search_products_by_name(
    product_name: Optional[str] = Query(None, description="Product name to search for (prefix matching - matches from beginning only). If not provided, returns latest 10 products."),
    db: AsyncSession = Depends(get_db)
):

    try:
        if product_name:
            # Build the query to search products by name with prefix matching
            query = (
                select(Product, Category.category_name.label("category_name"))
                .join(Category, Product.category_id == Category.category_id)
                .where(Product.identification["product_name"].astext.ilike(f"{product_name}%"))
                .order_by(Product.timestamp.desc())
                .limit(10)
            )
            
            # Get total count of matching products
            count_query = (
                select(func.count(Product.product_id))
                .join(Category, Product.category_id == Category.category_id)
                .where(Product.identification["product_name"].astext.ilike(f"{product_name}%"))
            )
        else:
            # Build the query to get latest 10 products when no search term provided
            query = (
                select(Product, Category.category_name.label("category_name"))
                .join(Category, Product.category_id == Category.category_id)
                .order_by(Product.timestamp.desc())
                .limit(10)
            )
            
            # Get total count of all products
            count_query = select(func.count(Product.product_id))
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Execute the main query
        result = await db.execute(query)
        products_data = result.all()
        
        # Format the response
        products = []
        for product, category_name in products_data:
            # Extract product image (first available image)
            product_image = None
            if product.images and "urls" in product.images and product.images["urls"]:
                product_image = get_media_url(product.images["urls"][0])
            
            # Extract pricing
            product_pricing = None
            if product.pricing and product.pricing.get("selling_price"):
                product_pricing = product.pricing["selling_price"]
            
            # Extract product name
            product_name_value = product.identification.get("product_name", "")
            
            products.append(ProductSearchResponse(
                product_id=product.product_id,
                product_name=product_name_value,
                product_image=product_image,
                product_pricing=product_pricing,
                slug=product.slug,
                category=category_name
            ))
        
        return ProductSearchListResponse(
            products=products,
            total_count=total_count
        )
        
    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR,
            f"Failed to search products by name: {str(e)}",
            log_error=True,
        )

@router.get("/{product_id}", response_model=ProductResponse, status_code=200)
async def get_product_by_id(product_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Product, VendorLogin, BusinessProfile)
            .join(VendorLogin, Product.vendor_id == VendorLogin.user_id)
            .join(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
            .filter(Product.product_id == product_id)
        )
        product_data = result.first()

        if not product_data:
            return APIResponse.response(
                StatusCode.NOT_FOUND,
                f"Product with ID {product_id} not found",
                log_error=False,
            )
        
        product, vendor_login, business_profile = product_data

        # Fetch category/subcategory names
        category_result = await db.execute(select(Category.category_name).where(Category.category_id == product.category_id))
        category_name = category_result.scalar()

        subcategory_result = await db.execute(select(SubCategory.subcategory_name).where(SubCategory.subcategory_id == product.subcategory_id))
        subcategory_name = subcategory_result.scalar()

        # Process image URLs
        processed_images = product.images
        if product.images and "urls" in product.images:
            image_urls = [get_media_url(url) for url in product.images["urls"]]
            processed_images = {"urls": image_urls}

        # Build and return ProductResponse
        product_response = ProductResponse(
            product_id=product.product_id,
            store_name=business_profile.store_name if business_profile else None,
            slug=product.slug,
            identification=product.identification,
            descriptions=product.descriptions,
            pricing=product.pricing,
            inventory=product.inventory,
            physical_attributes=product.physical_attributes,
            images=processed_images,
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
            select(Product, VendorLogin, BusinessProfile)
            .join(VendorLogin, Product.vendor_id == VendorLogin.user_id)
            .join(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
            .where(Product.slug == slug)
            .options(
                selectinload(Product.category),
                selectinload(Product.subcategory)
            )
        )
        product_data = result.first()

        if not product_data:
            return APIResponse.response(
                StatusCode.NOT_FOUND,
                f"Product with slug '{slug}' not found",
                log_error=False,
            )
        
        product, vendor_login, business_profile = product_data

        # Process image URLs
        processed_images = product.images
        if product.images and "urls" in product.images:
            image_urls = [get_media_url(url) for url in product.images["urls"]]
            processed_images = {"urls": image_urls}

        return ProductResponse(
            product_id=product.product_id,
            store_name=business_profile.store_name if business_profile else None,
            slug=product.slug,
            identification=product.identification,
            descriptions=product.descriptions,
            pricing=product.pricing,
            inventory=product.inventory,
            physical_attributes=product.physical_attributes,
            images=processed_images,
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


@router.get("/by-vendor/{store_slug}", response_model=List[ProductResponse])
async def get_products_by_store_slug(
    store_slug: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        # First, find the vendor_id using the store_slug
        business_profile_result = await db.execute(
            select(BusinessProfile)
            .filter(BusinessProfile.store_slug == store_slug)
        )
        business_profile = business_profile_result.scalar_one_or_none()
        
        if not business_profile:
            raise HTTPException(
                status_code=404,
                detail=f"No store found with slug: {store_slug}"
            )
        
        # Get the vendor_id from the business profile
        vendor_result = await db.execute(
            select(VendorLogin)
            .filter(VendorLogin.business_profile_id == business_profile.profile_ref_id)
        )
        vendor = vendor_result.scalar_one_or_none()
        
        if not vendor:
            raise HTTPException(
                status_code=404,
                detail=f"No vendor found for store slug: {store_slug}"
            )
        
        # Now get products using the vendor_id
        result = await db.execute(
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.subcategory),
            )
            .filter(Product.vendor_id == vendor.user_id)
        )
        products = result.scalars().all()

        if not products:
            raise HTTPException(
                status_code=404,
                detail=f"No products found for store: {store_slug}"
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
                    store_name=business_profile.store_name,
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

    except HTTPException:
        # Re-raise HTTPException (like our 404) without modification
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve products: {str(e)}"
        )


@router.get("/by-vendor-id/{vendor_id}", response_model=VendorProductsResponse)
async def get_products_by_vendor_id(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        # First, verify vendor exists and get vendor details
        vendor_result = await db.execute(
            select(VendorLogin, BusinessProfile)
            .join(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
            .filter(VendorLogin.user_id == vendor_id)
        )
        vendor_data = vendor_result.first()
        
        if not vendor_data:
            raise HTTPException(
                status_code=404,
                detail=f"Vendor with ID {vendor_id} not found"
            )
        
        vendor_login, business_profile = vendor_data
        
        # Get products for this vendor
        result = await db.execute(
            select(Product, VendorLogin, BusinessProfile)
            .join(VendorLogin, Product.vendor_id == VendorLogin.user_id)
            .join(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
            .options(
                selectinload(Product.category),
                selectinload(Product.subcategory),
            )
            .filter(Product.vendor_id == vendor_id)
        )
        products_data = result.all()

        # Map products into the correct response model
        products_list = []
        for product, vendor_login, business_profile in products_data:
            image_urls = []
            if product.images and "urls" in product.images:
                image_urls = [get_media_url(url) for url in product.images["urls"]]

            products_list.append(
                ProductResponse(
                    product_id=product.product_id,
                    # banner_image=get_media_url(business_profile.business_logo) if business_profile else None,
                    # banner_title=business_profile.banner_title if business_profile else None,
                    # banner_subtitle=business_profile.banner_subtitle if business_profile else None,
                    store_name=business_profile.store_name if business_profile else None,
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

        # Return vendor details with products (empty list if no products)
        return VendorProductsResponse(
            vendor_id=vendor_id,
            store_name=business_profile.store_name if business_profile else None,
            banner_image=get_media_url(business_profile.business_logo) if business_profile and business_profile.business_logo else None,
            banner_title=business_profile.banner_title if business_profile else None,
            banner_subtitle=business_profile.banner_subtitle if business_profile else None,
            products=products_list,
            total_count=len(products_list)
        )

    except HTTPException:
        # Re-raise HTTPException (like our 404) without modification
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve products: {str(e)}"
        )



@router.put("/id/{product_id}", response_model=ProductResponse, status_code=200)
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
        identification_data = safe_json_parse(identification)
        if identification_data:
            product.identification = {**product.identification, **identification_data}

        descriptions_data = safe_json_parse(descriptions)
        if descriptions_data:
            product.descriptions = {**(product.descriptions or {}), **descriptions_data}

        pricing_data = safe_json_parse(pricing)
        if pricing_data:
            product.pricing = {**(product.pricing or {}), **pricing_data}

        inventory_data = safe_json_parse(inventory)
        if inventory_data:
            product.inventory = {**(product.inventory or {}), **inventory_data}

        physical_attributes_data = safe_json_parse(physical_attributes)
        if physical_attributes_data:
            product.physical_attributes = {**(product.physical_attributes or {}), **physical_attributes_data}

        tags_and_relationships_data = safe_json_parse(tags_and_relationships)
        if tags_and_relationships_data:
            product.tags_and_relationships = {**(product.tags_and_relationships or {}), **tags_and_relationships_data}

        status_flags_data = safe_json_parse(status_flags)
        if status_flags_data:
            product.status_flags = {**product.status_flags, **status_flags_data}
    except json.JSONDecodeError as e:
        return APIResponse.response(StatusCode.BAD_REQUEST, f"Invalid JSON data: {str(e)}", log_error=True)

    # Update slug if product name was changed
    if identification_data and "product_name" in identification_data:
        new_product_name = identification_data["product_name"].strip()
        if new_product_name:
            new_slug = await generate_unique_slug(new_product_name, db, product_id)
            product.slug = new_slug

    if files:
        try:
            image_urls = []
            product_name = product.identification.get("product_name", "").replace(" ", "_").lower()
            cleaned_product_id = product_id.replace(" ", "_").lower()

            for file in files:
                # Read file content as bytes
                file_content = await file.read()
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                new_filename = f"{timestamp}_{file.filename}"
                file_path = f"products/{product_name}/{cleaned_product_id}/{new_filename}"
                
                # Upload file to S3 and get the URL
                image_url = await upload_file_to_s3(
                    file_content=file_content,
                    file_path=file_path,
                    file_type=file.content_type
                )
                image_urls.append(image_url)

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
    
    # Fetch store_name from business profile
    store_name = None
    vendor_result = await db.execute(
        select(VendorLogin)
        .options(selectinload(VendorLogin.business_profile))
        .filter(VendorLogin.user_id == product.vendor_id)
    )
    vendor = vendor_result.scalars().first()
    if vendor and vendor.business_profile:
        store_name = vendor.business_profile.store_name

    return ProductResponse(
        product_id=product.product_id,
        store_name=store_name,
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


@router.put("/slug/{slug}", response_model=ProductResponse, status_code=200)
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
        identification_data = safe_json_parse(identification)
        if identification_data:
            product.identification = {**product.identification, **identification_data}

        descriptions_data = safe_json_parse(descriptions)
        if descriptions_data:
            product.descriptions = {**(product.descriptions or {}), **descriptions_data}

        pricing_data = safe_json_parse(pricing)
        if pricing_data:
            product.pricing = {**(product.pricing or {}), **pricing_data}

        inventory_data = safe_json_parse(inventory)
        if inventory_data:
            product.inventory = {**(product.inventory or {}), **inventory_data}

        physical_attributes_data = safe_json_parse(physical_attributes)
        if physical_attributes_data:
            product.physical_attributes = {**(product.physical_attributes or {}), **physical_attributes_data}

        tags_and_relationships_data = safe_json_parse(tags_and_relationships)
        if tags_and_relationships_data:
            product.tags_and_relationships = {**(product.tags_and_relationships or {}), **tags_and_relationships_data}

        status_flags_data = safe_json_parse(status_flags)
        if status_flags_data:
            product.status_flags = {**product.status_flags, **status_flags_data}
    except json.JSONDecodeError as e:
        return APIResponse.response(StatusCode.BAD_REQUEST, f"Invalid JSON data: {str(e)}", log_error=True)

    # Update slug if product name was changed
    if identification_data and "product_name" in identification_data:
        new_product_name = identification_data["product_name"].strip()
        if new_product_name:
            new_slug = await generate_unique_slug(new_product_name, db, product.product_id)
            product.slug = new_slug

    if files:
        try:
            image_urls = []
            product_name = product.identification.get("product_name", "").replace(" ", "_").lower()
            cleaned_slug = slug.replace(" ", "_").lower()

            for file in files:
                # Read file content as bytes
                file_content = await file.read()
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                new_filename = f"{timestamp}_{file.filename}"
                file_path = f"products/{product_name}/{cleaned_slug}/{new_filename}"
                
                # Upload file to S3 and get the URL
                image_url = await upload_file_to_s3(
                    file_content=file_content,
                    file_path=file_path,
                    file_type=file.content_type
                )
                image_urls.append(image_url)

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
    
    # Fetch store_name from business profile
    store_name = None
    vendor_result = await db.execute(
        select(VendorLogin)
        .options(selectinload(VendorLogin.business_profile))
        .filter(VendorLogin.user_id == product.vendor_id)
    )
    vendor = vendor_result.scalars().first()
    if vendor and vendor.business_profile:
        store_name = vendor.business_profile.store_name

    return ProductResponse(
        product_id=product.product_id,
        store_name=store_name,
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


@router.put("/slug/delete/{slug}", response_model=Dict)
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



@router.put("/delete/{product_id}", response_model=Dict)
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


@router.put("/restore/{product_id}", response_model=Dict)
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


@router.put("/slug/restore/{slug}", response_model=Dict)
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


@router.get("/category/{slug}", response_model=ProductByCategoryListResponse, status_code=200)
async def get_products_by_category_or_subcategory_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        # First, try to find a category by slug
        category_result = await db.execute(
            select(Category).filter(Category.category_slug == slug)
        )
        category = category_result.scalars().first()
        
        subcategory = None
        slug_type = None
        category_name = None
        subcategory_name = None
        
        if category:
            # Found a category
            slug_type = "category"
            category_name = category.category_name
            
            # Get all products for this category with business profile
            products_query = (
                select(Product, VendorLogin, BusinessProfile)
                .join(VendorLogin, Product.vendor_id == VendorLogin.user_id)
                .join(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
                .filter(Product.category_id == category.category_id)
            )
            count_query = select(func.count(Product.product_id)).filter(Product.category_id == category.category_id)
            
        else:
            # Try to find a subcategory by slug
            subcategory_result = await db.execute(
                select(SubCategory)
                .filter(SubCategory.subcategory_slug == slug)
                .options(selectinload(SubCategory.category))
            )
            subcategory = subcategory_result.scalars().first()
            
            if not subcategory:
                return APIResponse.response(
                    StatusCode.NOT_FOUND,
                    f"Category or subcategory with slug '{slug}' not found",
                    log_error=False,
                )
            
            # Found a subcategory
            slug_type = "subcategory"
            category_name = subcategory.category.category_name
            subcategory_name = subcategory.subcategory_name
            
            # Get all products for this subcategory with business profile
            products_query = (
                select(Product, VendorLogin, BusinessProfile)
                .join(VendorLogin, Product.vendor_id == VendorLogin.user_id)
                .join(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
                .filter(Product.subcategory_id == subcategory.subcategory_id)
            )
            count_query = select(func.count(Product.product_id)).filter(Product.subcategory_id == subcategory.subcategory_id)

        # Add options to load relationships
        products_query = products_query.options(
            selectinload(Product.category),
            selectinload(Product.subcategory)
        )

        # Execute queries
        products_result = await db.execute(products_query)
        products_data = products_result.all()

        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        # Convert ORM objects to simplified response format
        product_responses = []
        for product, vendor_login, business_profile in products_data:
            # Get thumbnail image (first image if available)
            thumbnail_image = None
            if product.images and "urls" in product.images and product.images["urls"]:
                thumbnail_image = get_media_url(product.images["urls"][0])

            # Extract data from JSON fields
            product_name = product.identification.get("product_name", "") if product.identification else ""
            product_sku = product.identification.get("product_sku", "") if product.identification else None
            short_description = product.descriptions.get("short_description", "") if product.descriptions else None
            selling_price = product.pricing.get("selling_price", "") if product.pricing else None
            actual_price = product.pricing.get("actual_price", "") if product.pricing else None

            stock = product.inventory.get("quantity", "") if product.inventory else None
            stock_alert_status = product.inventory.get("stock_alert_status", "") if product.inventory else None
            
            # Extract status flags
            featured_product = product.status_flags.get("featured_product", False) if product.status_flags else False
            published_product = product.status_flags.get("published_product", True) if product.status_flags else True
            product_status = product.status_flags.get("product_status", False) if product.status_flags else False

            product_response = ProductByCategoryResponse(
                product_id=product.product_id,
                product_name=product_name,
                product_sku=product_sku,
                stock = stock,
                stock_alert_status= stock_alert_status,
                slug=product.slug,
                short_description=short_description,
                selling_price=selling_price,
                actual_price=actual_price,
                thumbnail_image=thumbnail_image,
                featured_product=featured_product,
                published_product=published_product,
                product_status=product_status,
                timestamp=product.timestamp,
                category_name=category_name,
                subcategory_name=product.subcategory.subcategory_name if product.subcategory else None,
                store_name=business_profile.store_name if business_profile else None,
            )
            product_responses.append(product_response)

        return ProductByCategoryListResponse(
            products=product_responses,
            total_count=total_count,
            slug=slug,
            slug_type=slug_type,
            category_name=category_name,
            subcategory_name=subcategory_name
        )

    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR,
            f"Failed to retrieve products by category slug: {str(e)}",
            log_error=True,
        )
