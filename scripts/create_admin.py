import asyncio
import sys
import argparse
from getpass import getpass
from src.infrastructure.database import AsyncSessionFactory
from src.models.user import User, UserType
from src.security.passwords import hash_password
from sqlalchemy import select

async def main():
    parser = argparse.ArgumentParser(description="Create a new admin user.")
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--password", help="Admin password")
    parser.add_argument("--first-name", help="Admin first name")
    parser.add_argument("--last-name", help="Admin last name (optional)")
    parser.add_argument("--email", help="Admin email address (optional)")
    args = parser.parse_args()

    username = args.username
    password = args.password
    first_name = args.first_name
    last_name = args.last_name
    email = args.email

    if not username:
        username = input("Enter admin username: ").strip()
    if not username:
        print("Error: Username is required.")
        sys.exit(1)

    if not first_name:
        first_name = input("Enter admin first name: ").strip()
    if not first_name:
        print("Error: First name is required.")
        sys.exit(1)

    # Optional fields interactive prompts
    if last_name is None:
        last_name = input("Enter admin last name (optional, press Enter to skip): ").strip()
        if not last_name:
            last_name = None

    if email is None:
        email = input("Enter admin email (optional, press Enter to skip): ").strip()
        if not email:
            email = None

    if not password:
        password = getpass("Enter admin password: ").strip()
    if not password:
        print("Error: Password is required.")
        sys.exit(1)

    async with AsyncSessionFactory() as session:
        try:
            # Check if username already exists
            stmt = select(User).where(User.username == username)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                print(f"Error: A user with username '{username}' already exists (type: {existing.type}).")
                sys.exit(1)

            # Check if email already exists
            if email:
                stmt_email = select(User).where(User.email == email)
                res_email = await session.execute(stmt_email)
                existing_email = res_email.scalar_one_or_none()
                if existing_email:
                    print(f"Error: A user with email '{email}' already exists.")
                    sys.exit(1)

            hashed = hash_password(password)
            admin_user = User(
                first_name=first_name,
                last_name=last_name,
                username=username,
                phone=None,
                email=email,
                password=hashed,
                type=UserType.ADMIN,
                is_active=True,
                is_superuser=True
            )
            session.add(admin_user)
            await session.commit()
            print(f"Success: Admin user created successfully (ID: {admin_user.id}, Username: {username}).")
        except Exception as e:
            print(f"Database error: {e}")
            await session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
