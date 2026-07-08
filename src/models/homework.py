from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from src.infrastructure.database import Base

class HomeworkType:
    TEST = "test"
    TEXT = "text"
    FILE = "file"
    NONE = "none"

    ALL = (TEST, TEXT, FILE, NONE)

class Homework(Base):
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    type = Column(String, nullable=False, default=HomeworkType.NONE)
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lesson = relationship("Lesson", back_populates="homework")
    test_detail = relationship(
        "TestHomework", back_populates="homework", uselist=False, cascade="all, delete-orphan"
    )
    text_detail = relationship(
        "TextHomework", back_populates="homework", uselist=False, cascade="all, delete-orphan"
    )
    file_detail = relationship(
        "FileHomework", back_populates="homework", uselist=False, cascade="all, delete-orphan"
    )

class TestHomework(Base):
    __tablename__ = "test_homeworks"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    timer_minutes = Column(Integer, nullable=True)
    pass_ball = Column(Integer, nullable=False, default=0)

    homework = relationship("Homework", back_populates="test_detail")
    questions = relationship(
        "TestQuestion",
        back_populates="test_homework",
        cascade="all, delete-orphan",
        order_by="TestQuestion.order_index",
    )

class TestQuestion(Base):
    __tablename__ = "test_questions"

    id = Column(Integer, primary_key=True, index=True)
    test_homework_id = Column(Integer, ForeignKey("test_homeworks.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    ball = Column(Integer, nullable=False, default=0)
    order_index = Column(Integer, nullable=False, default=0)

    test_homework = relationship("TestHomework", back_populates="questions")
    options = relationship(
        "TestQuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="TestQuestionOption.order_index",
    )

class TestQuestionOption(Base):
    __tablename__ = "test_question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("test_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    order_index = Column(Integer, nullable=False, default=0)

    question = relationship("TestQuestion", back_populates="options")

class TextHomework(Base):
    __tablename__ = "text_homeworks"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    deadline_days = Column(Integer, nullable=False)
    pass_ball = Column(Integer, nullable=False, default=0)
    min_words = Column(Integer, nullable=False, default=0)
    grading_criteria = Column(JSONB, nullable=True)  # e.g. {"200 so'z yozsangiz": "90 ball"}

    homework = relationship("Homework", back_populates="text_detail")

class FileHomework(Base):
    __tablename__ = "file_homeworks"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    deadline_days = Column(Integer, nullable=False)
    file_formats = Column(JSONB, nullable=False, default=list)  # e.g. [".pdf", ".xlsx"]
    max_file_size_mb = Column(Integer, nullable=False)
    example_file = Column(String, nullable=True)

    homework = relationship("Homework", back_populates="file_detail")
