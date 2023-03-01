from typing import List

from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from sqlalchemy import select
from sqlalchemy import DateTime

from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Session

import datetime

engine = create_engine("sqlite+pysqlite:///logs.db", echo=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    username: Mapped[str]
    messages: Mapped[List["Messages"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, first_name={self.name!r}, username={self.fullname!r})"


class Messages(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False))
    text: Mapped[str]
    state: Mapped[str]
    user_id = mapped_column(ForeignKey("user_account.id"))
    user: Mapped[User] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"Messages(id={self.id!r}, date={self.date!r}, text={self.text!r}, state={self.state!r})"


Base.metadata.create_all(engine)


def get_user(uid):
    with Session(engine) as session:
        user = session.execute(select(User).filter_by(id=uid)).first()
    return user


def put_user(user_id, first_name, username):
    with Session(engine) as session:
        user = User(id=user_id, first_name=first_name, username=username)
        session.add(user)
        session.commit()


# def put_message(date, text, state, user_id):
#     with Session(engine) as session:
#         message = Messages(date=date, text=text, state=state)
#         user = session.execute(select(User).filter_by(id=user_id)).scalar_one()
#         user.messages.append(message)
#         session.commit()
