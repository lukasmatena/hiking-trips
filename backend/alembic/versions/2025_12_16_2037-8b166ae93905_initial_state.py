"""Initial state

Revision ID: 8b166ae93905
Revises: 
Create Date: 2025-12-16 20:37:37.343656

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b166ae93905'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""CREATE TABLE trips (
                    trip_id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    description TEXT,
                    date_start DATE,
                    date_end DATE);
                CREATE TABLE photos (
                    photo_id SERIAL PRIMARY KEY,
                    trip_id INT,
                    s3_key TEXT,
                    CONSTRAINT fk_trips_photos
                        FOREIGN KEY (trip_id)
                        REFERENCES trips(trip_id)
                        ON DELETE RESTRICT
                );""")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE trips; DROP TABLE photos;")
