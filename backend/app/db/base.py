# backend/app/db/base_class.py
from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    """Custom abstract base providing global multi-platform table configurations automatically."""
    
    @declared_attr
    def __tablename__(cls) -> str:
        # Converts CamelCase models into snake_case database tables seamlessly
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()