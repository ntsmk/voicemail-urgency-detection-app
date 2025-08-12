from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Voicemails(db.Model):
    ticket_id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str]