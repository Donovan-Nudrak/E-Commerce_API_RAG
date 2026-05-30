import logging

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.role import Role
from app.models.category import Category
from app.models.customer import Customer
from app.models.payment_type import PaymentType
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_roles(db: Session) -> None:
    roles = ["Customer", "Administrator"]

    for role_name in roles:
        exists = db.query(Role).filter(Role.name == role_name).first()
        if not exists:
            db.add(Role(name=role_name))
            logger.info(f"Role created: {role_name}")

    db.commit()


def seed_categories(db: Session) -> None:
    categories = [
        "Electronics",
        "Clothing",
        "Food & Beverages",
        "Home & Garden",
        "Sports",
    ]

    for category_name in categories:
        exists = db.query(Category).filter(Category.name == category_name).first()
        if not exists:
            db.add(Category(name=category_name))
            logger.info(f"Category created: {category_name}")

    db.commit()


def seed_payment_types(db: Session) -> None:
    payment_types = ["Card", "Bank Transfer", "Cash"]

    for type_name in payment_types:
        exists = db.query(PaymentType).filter(PaymentType.name == type_name).first()
        if not exists:
            db.add(PaymentType(name=type_name))
            logger.info(f"Payment type created: {type_name}")

    db.commit()


def seed_admin(db: Session) -> None:
    admin_email = "admin@ecommerce.com"

    exists = db.query(Customer).filter(Customer.email == admin_email).first()
    if exists:
        logger.info("Admin already exists, skipping.")
        return

    admin_role = db.query(Role).filter(Role.name == "Administrator").first()

    admin = Customer(
        role_id=admin_role.id,
        first_name="Admin",
        last_name="Ecommerce",
        email=admin_email,
        password_hash=hash_password("admin1234"),
    )

    db.add(admin)
    db.commit()
    logger.info(f"Admin created: {admin_email}")


def run_seed() -> None:
    db = SessionLocal()
    try:
        logger.info("Starting seed...")
        seed_roles(db)
        seed_categories(db)
        seed_payment_types(db)
        seed_admin(db)
        logger.info("Seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
