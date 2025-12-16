# services/favorite_service.py
from models.storage import storage


class FavoriteService:
    @staticmethod
    def add_to_favorites(user_id: int, post_id: int) -> bool:
        """Добавляет пост в избранное пользователя"""
        # Проверяем существование пользователя и поста
        user = storage.get_user_by_id(user_id)
        post = storage.get_post_by_id(post_id)

        if not user or not post:
            return False

        return storage.add_to_favorites(user_id, post_id)

    @staticmethod
    def remove_from_favorites(user_id: int, post_id: int) -> bool:
        """Удаляет пост из избранного"""
        return storage.remove_from_favorites(user_id, post_id)

    @staticmethod
    def get_user_favorites(user_id: int):
        """Возвращает избранные посты пользователя"""
        user = storage.get_user_by_id(user_id)
        if not user:
            raise ValueError("Пользователь не найден")

        return storage.get_user_favorites(user_id)

    @staticmethod
    def is_post_in_favorites(user_id: int, post_id: int) -> bool:
        """Проверяет, есть ли пост в избранном"""
        return storage.is_post_in_favorites(user_id, post_id)
