import uuid

from sqlalchemy.orm import Session

import models


def get_category(db: Session, category_id: str):
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def get_category_by_name(db: Session, name: str):
    return db.query(models.Category).filter(models.Category.name == name).first()


def delete_category(db: Session, category_id: str):
    instance = db.query(models.Category).filter(models.Category.id == category_id).first()
    db.delete(instance)
    db.commit()


def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Category).offset(skip).limit(limit).all()


def create_category(db: Session, name):
    id = str(uuid.uuid4())
    db_category = models.Category(id=id, name=name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def get_question(db: Session, question_id: str):
    return db.query(models.Question).filter(models.Question.id == question_id).first()


def delete_question(db: Session, question_id: str):
    instance = db.query(models.Question).filter(models.Question.id == question_id).first()
    db.delete(instance)
    db.commit()


def get_questions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Question).offset(skip).limit(limit).all()


def create_question(db: Session, name, text, photo, answers, cor_answers, score, category_id):
    id = str(uuid.uuid4())
    db_question = models.Question(
        id=id,
        name=name,
        text=text,
        photo=photo,
        answers=answers,
        cor_answers=cor_answers,
        score=score,
        category_id=category_id
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


def get_user(db: Session, users_id: str):
    return db.query(models.Users).filter(models.Users.id == users_id).first()


def get_user_by_chat(db: Session, chat_id: str):
    return db.query(models.Users).filter(models.Users.chat_id == chat_id).first()


def delete_user(db: Session, users_id: str):
    instance = db.query(models.Users).filter(models.Users.id == users_id).first()
    db.delete(instance)
    db.commit()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Users).offset(skip).limit(limit).all()


def create_user(db: Session, chat_id, email):
    id = str(uuid.uuid4())
    db_users = models.Users(
        id=id,
        chat_id=chat_id,
        email=email
    )
    db.add(db_users)
    db.commit()
    db.refresh(db_users)
    return db_users


# def update_user(db: Session, chat_id, score):
#     user = db.query(models.Users).filter(models.Users.chat_id == chat_id).update(
#         {
#             models.Users.score: score
#         }
#     )
#     db.commit()
#     return user


def get_user_question_by_user(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.UsersQuestion).filter(models.UsersQuestion.users_id == user_id).offset(skip).limit(
        limit).all()


def get_user_question_by_chat(db: Session, chat_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.UsersQuestion).filter(models.UsersQuestion.chat_id == chat_id).offset(skip).limit(
        limit).all()


def get_user_question_by_question(db: Session, question_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.UsersQuestion).filter(models.UsersQuestion.question_id == question_id).offset(skip).limit(
        limit).all()


def get_user_question_by_u_q(db: Session, users_id: str, question_id):
    return db.query(models.UsersQuestion).filter(
        models.UsersQuestion.users_id == users_id).filter(models.UsersQuestion.question_id == question_id).first()


def get_user_question_by_c_q(db: Session, chat_id: str, question_id):
    return db.query(models.UsersQuestion).filter(
        models.UsersQuestion.chat_id == chat_id).filter(models.UsersQuestion.question_id == question_id).first()


def delete_user_question_by_u_q(db: Session, users_id: str, question_id):
    instance = db.query(models.UsersQuestion).filter(
        models.UsersQuestion.users_id == users_id).filter(models.UsersQuestion.question_id == question_id).first()
    db.delete(instance)
    db.commit()


def get_users_question(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.UsersQuestion).offset(skip).limit(limit).all()


def create_user_question(db: Session, users_id, chat_id, question_id, answers, score):
    db_users_question = models.UsersQuestion(
        users_id=users_id,
        chat_id=chat_id,
        question_id=question_id,
        answers=answers,
        score=score
    )
    db.add(db_users_question)
    db.commit()
    db.refresh(db_users_question)
    return db_users_question


def get_user_score(db: Session, users_id: str, category_id: str):
    return db.query(models.UsersScore).filter(
        models.UsersScore.users_id == users_id).filter(models.UsersScore.category_id == category_id).first()


def create_user_score(db: Session, users_id: str, category_id: str):
    db_users_score = models.UsersScore(
        users_id=users_id,
        category_id=category_id,
        score=0
    )
    db.add(db_users_score)
    db.commit()
    db.refresh(db_users_score)
    return db_users_score


def update_user_score(db: Session, users_id: str, category_id: str, score: int):
    score = db.query(models.UsersScore).filter(
        models.UsersScore.users_id == users_id).filter(models.UsersScore.category_id == category_id
    ).update({models.UsersScore.score: score})
    db.commit()
    return score


def get_user_scores(db: Session, users_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.UsersScore).filter(
        models.UsersScore.users_id == users_id
    ).offset(skip).limit(limit).all()
