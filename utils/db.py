from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from typing import Optional

def get_db_engine(
    host: str,
    database: str,
    user: str,
    port: int = 5432,
    password: Optional[str] = None
) -> Engine:
    """
    Creates a SQLAlchemy Engine for a PostgreSQL database with GSSAPI support.

    Args:
        host: The database host.
        database: The database name.
        user: The database user.
        port: The database port (default: 5432).
        password: The database password (optional).

    Returns:
        A SQLAlchemy Engine object.
    """
    # Construct the connection string
    # If password is provided, include it. Otherwise, assume GSSAPI handles auth or password is not needed in string.
    # Note: For GSSAPI, password might not be strictly required in the URL if the ticket is present,
    # but if provided, we include it.
    if password:
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    else:
        url = f"postgresql+psycopg2://{user}@{host}:{port}/{database}"

    # Create the engine with GSSAPI options
    # gssencmode='prefer' tells libpq to prefer GSSAPI encryption
    engine = create_engine(
        url,
        connect_args={'gssencmode': 'prefer'}
    )

    return engine
