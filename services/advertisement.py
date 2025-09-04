from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.superadmin import Advertisement


class AdvertisementService:
    """Service class for advertisement operations."""

    @staticmethod
    async def create_advertisement(
        db: AsyncSession,
        id: str,
        title: str,
        banner: str,
        target_url: Optional[str] = None,
    ) -> Advertisement:
        """
        Create a new advertisement.

        Args:
            db: Database session
            title: Advertisement title
            banner: Banner image path
            target_url: Optional target URL

        Returns:
            Advertisement: The created advertisement
        """
        new_advertisement = Advertisement(
            ad_id=id,
            title=title,
            banner=banner,
            target_url=target_url,
        )

        db.add(new_advertisement)
        await db.commit()
        await db.refresh(new_advertisement)
        return new_advertisement

    @staticmethod
    async def get_advertisement_by_id(
        db: AsyncSession, ad_id: str
    ) -> Optional[Advertisement]:
        """
        Get advertisement by ID.

        Args:
            db: Database session
            ad_id: Advertisement ID

        Returns:
            Optional[Advertisement]: The advertisement if found
        """
        stmt = select(Advertisement).where(Advertisement.ad_id == ad_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_advertisements(
        db: AsyncSession,
        status_filter: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Advertisement]:
        """
        Get all advertisements with optional filtering and pagination.

        Args:
            db: Database session
            status_filter: Optional filter by advertisement status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Advertisement]: List of advertisements
        """
        stmt = select(Advertisement)

        # Apply status filter if provided
        if status_filter is not None:
            stmt = stmt.where(Advertisement.ad_status == status_filter)

        # Apply pagination and ordering
        stmt = (
            stmt.order_by(Advertisement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_active_advertisements(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Advertisement]:
        """
        Get all active advertisements.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Advertisement]: List of active advertisements
        """
        stmt = (
            select(Advertisement)
            .where(Advertisement.ad_status == False)
            .order_by(Advertisement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_advertisement(
        db: AsyncSession,
        ad_id: str,
        title: Optional[str] = None,
        banner: Optional[str] = None,
        target_url: Optional[str] = None,
    ) -> Optional[Advertisement]:
        """
        Update an advertisement.

        Args:
            db: Database session
            ad_id: Advertisement ID
            title: Optional new title
            banner: Optional new banner path
            target_url: Optional new target URL

        Returns:
            Optional[Advertisement]: The updated advertisement if found
        """
        advertisement = await AdvertisementService.get_advertisement_by_id(
            db, ad_id
        )
        if not advertisement:
            return None

        # Update fields if provided
        if title is not None:
            advertisement.title = title
        if banner is not None:
            advertisement.banner = banner
        if target_url is not None:
            advertisement.target_url = target_url

        await db.commit()
        await db.refresh(advertisement)
        return advertisement

    @staticmethod
    async def toggle_advertisement_status(
        db: AsyncSession, ad_id: str
    ) -> Optional[Advertisement]:
        """
        Toggle advertisement status (active/inactive).

        Args:
            db: Database session
            ad_id: Advertisement ID

        Returns:
            Optional[Advertisement]: The updated advertisement if found
        """
        advertisement = await AdvertisementService.get_advertisement_by_id(
            db, ad_id
        )
        if not advertisement:
            return None

        advertisement.ad_status = not advertisement.ad_status
        await db.commit()
        await db.refresh(advertisement)
        return advertisement

    @staticmethod
    async def delete_advertisement(db: AsyncSession, ad_id: str) -> bool:
        """
        Delete an advertisement.

        Args:
            db: Database session
            ad_id: Advertisement ID

        Returns:
            bool: True if deleted, False if not found
        """
        advertisement = await AdvertisementService.get_advertisement_by_id(
            db, ad_id
        )
        if not advertisement:
            return False

        delete_stmt = delete(Advertisement).where(Advertisement.ad_id == ad_id)
        await db.execute(delete_stmt)
        await db.commit()
        return True
