from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, ARRAY, LargeBinary, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref

from database import Base


class Category(Base):
    __tablename__ = "category"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)


class Question(Base):
    __tablename__ = "question"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    text = Column(String)
    photo = Column(LargeBinary, nullable=True)
    answers = Column(ARRAY(String))
    cor_answers = Column(ARRAY(String))
    score = Column(Integer)
    category_id = Column(String, ForeignKey("category.id"))
    category = relationship(Category, backref=backref("question", cascade="all,delete"))


class Users(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String)
    chat_id = Column(Integer)


class UsersQuestion(Base):
    __tablename__ = "users_question"

    users_id = Column(String, ForeignKey("users.id"), primary_key=True, index=True)
    chat_id = Column(Integer, primary_key=True, index=True)
    question_id = Column(String, ForeignKey("question.id"), primary_key=True, index=True)
    answers = Column(ARRAY(String))
    score = Column(Integer)
    user = relationship(Users, backref=backref("users_question", cascade="all,delete"))
    question = relationship(Question, backref=backref("users_question", cascade="all,delete"))


class UsersScore(Base):
    __tablename__ = "users_score"

    users_id = Column(String, ForeignKey("users.id"), primary_key=True, index=True)
    category_id = Column(String, ForeignKey("category.id"), primary_key=True, index=True)
    score = Column(Integer)
    user = relationship(Users, backref=backref("users_score", cascade="all,delete"))
    category = relationship(Category, backref=backref("users_score", cascade="all,delete"))

