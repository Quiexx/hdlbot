from typing import List

from pydantic import BaseModel
from uuid import UUID


class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: str

    class Config:
        orm_mode = True


class QuestionBase(BaseModel):
    name: str
    text: str
    photo: bytearray
    answers: List[str]
    cor_answers: List[str]
    score: int


class QuestionCreate(CategoryBase):
    pass


class Question(CategoryBase):
    id: str
    category_id: str

    class Config:
        orm_mode = True


class UsersBase(BaseModel):
    email: str
    chat_id: int


class UsersCreate(CategoryBase):
    pass


class Users(CategoryBase):
    id: int

    class Config:
        orm_mode = True


class UsersQuestionBase(BaseModel):
    answers: List[str]
    score = int


class UsersQuestionCreate(CategoryBase):
    pass


class UsersQuestion(CategoryBase):
    users_id: int
    chat_id: int
    question_id: str

    class Config:
        orm_mode = True


class UsersScoreBase(BaseModel):
    score = int


class UsersScoreCreate(CategoryBase):
    pass


class UsersScore(CategoryBase):
    users_id: int
    category_id: str

    class Config:
        orm_mode = True
