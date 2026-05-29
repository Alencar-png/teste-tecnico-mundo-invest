from sqlalchemy.orm import Session, joinedload
from config.database import SessionLocal
from abc import abstractmethod, ABC
from fastapi import Depends


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CRUDBase(ABC):
    @property
    @abstractmethod
    def _entity(self):
        pass

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def find_one(self):
        pass

    @abstractmethod
    def find_all(self):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def delete(self):
        pass


class BaseRepository():
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def create(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def find_one(self, entity, item_id: int, relations: list[str] = None):
        load_options = []
        if relations:
            load_options = [joinedload(getattr(entity, rel))
                            for rel in relations]
        return self.db.query(entity).options(load_options).filter_by(id=item_id).first()

    def find_all(self, entity, relations: list[str] = None):
        load_options = []
        if relations:
            load_options = [joinedload(getattr(entity, rel))
                            for rel in relations]
        return self.db.query(entity).options(load_options).all()

    def update_one(self, entity, item_id: int, current_object, item):
        try:
            for key, value in item.dict(exclude_unset=True).items():
                if value is not None:  # Só atualiza campos que não são None
                    setattr(current_object, key, value)
            self.db.commit()
            updated_object = self.db.query(entity).get(item_id)
            return updated_object
        except Exception as e:
            self.db.rollback()
            raise e

    def delete_one(self, entity, item_id: int):
        try:
            object_to_delete = self.db.query(
                entity).filter_by(id=item_id).first()
            if object_to_delete:
                self.db.delete(object_to_delete)
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
