from __future__ import annotations

import html
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any


class BaseStorage(ABC):
    """Абстрактный класс хранилища (принцип абстракции)."""

    @abstractmethod
    def load(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def save(self, items: list[dict[str, Any]]) -> None:
        pass


class JsonStorage(BaseStorage):
    """Работа с JSON-файлом (наследование и полиморфизм)."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)
        self._root_key: str | None = None

    def load(self) -> list[dict[str, Any]]:
        if not self._file_path.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self.save([])
            return []

        try:
            with self._file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as err:
            raise ValueError(f"Файл {self._file_path.name} содержит некорректный JSON.") from err
        except OSError as err:
            raise RuntimeError(f"Не удалось прочитать {self._file_path.name}: {err}") from err

        if isinstance(data, list):
            self._root_key = None
            return [item for item in data if isinstance(item, dict)]

        if isinstance(data, dict):
            for key in ("books", "items", "catalog"):
                if isinstance(data.get(key), list):
                    self._root_key = key
                    return [item for item in data[key] if isinstance(item, dict)]

        raise ValueError("Ожидался список книг в JSON-файле.")

    def save(self, items: list[dict[str, Any]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        payload: Any = {self._root_key: items} if self._root_key else items

        try:
            with self._file_path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
        except OSError as err:
            raise RuntimeError(f"Не удалось сохранить {self._file_path.name}: {err}") from err


class Book:
    """Модель книги с валидацией данных (принцип инкапсуляции)."""

    def __init__(
        self,
        book_id: int,
        title: str,
        author: str,
        genre: str,
        year: int | str | None = None,
        description: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._id = int(book_id)
        self.title = title
        self.author = author
        self.genre = genre
        self.year = year
        self.description = description
        self._extra = extra or {}

    @property
    def id(self) -> int:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Название книги не может быть пустым.")
        self._title = cleaned

    @property
    def author(self) -> str:
        return self._author

    @author.setter
    def author(self, value: str) -> None:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Имя автора не может быть пустым.")
        self._author = cleaned

    @property
    def genre(self) -> str:
        return self._genre

    @genre.setter
    def genre(self, value: str) -> None:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Жанр не может быть пустым.")
        self._genre = cleaned

    @property
    def year(self) -> int | None:
        return self._year

    @year.setter
    def year(self, value: int | str | None) -> None:
        if value is None or str(value).strip() == "":
            self._year = None
            return
        try:
            parsed = int(value)
        except (TypeError, ValueError) as err:
            raise ValueError("Год издания должен быть целым числом.") from err

        max_year = datetime.now().year + 1
        if not (1000 <= parsed <= max_year):
            raise ValueError(f"Укажите год от 1000 до {max_year}.")
        self._year = parsed

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str | None) -> None:
        self._description = str(value or "").strip()

    @classmethod
    def from_dict(cls, raw: dict[str, Any], fallback_id: int) -> Book:
        try:
            book_id = int(raw.get("id", fallback_id))
        except (TypeError, ValueError):
            book_id = fallback_id

        title = raw.get("title") or raw.get("name") or raw.get("название") or "Без названия"
        author = raw.get("author") or raw.get("автор") or "Неизвестный автор"

        raw_genre = raw.get("genre") or raw.get("genres") or raw.get("жанр") or "Без жанра"
        if isinstance(raw_genre, list):
            genre = ", ".join(str(g).strip() for g in raw_genre if str(g).strip()) or "Без жанра"
        else:
            genre = str(raw_genre)

        year = raw.get("year") if raw.get("year") is not None else raw.get("год")
        description = raw.get("description") or raw.get("desc") or raw.get("описание") or ""

        known = {
            "id", "title", "name", "название", "author", "автор",
            "genre", "genres", "жанр", "year", "год",
            "description", "desc", "описание",
        }
        extra = {k: v for k, v in raw.items() if k not in known}
        return cls(book_id, str(title), str(author), genre, year, str(description), extra)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self._id,
            "title": self._title,
            "author": self._author,
            "genre": self._genre,
        }
        if self._year is not None:
            data["year"] = self._year
        if self._description:
            data["description"] = self._description
        data.update(self._extra)
        return data

    def format_card(self) -> str:
        year_text = str(self._year) if self._year is not None else "не указан"
        lines = [
            f"📖 <b>{html.escape(self._title)}</b>",
            f"✍️ <b>Автор:</b> {html.escape(self._author)}",
            f"🏷 <b>Жанр:</b> {html.escape(self._genre)}",
            f"📅 <b>Год:</b> {year_text}",
            f"🆔 <b>ID:</b> {self._id}",
        ]
        if self._description:
            lines.append(f"\n📝 {html.escape(self._description)}")
        return "\n".join(lines)


class BookCatalog:
    """Управление каталогом книг: поиск, фильтрация, сортировка, добавление, изменение."""

    def __init__(self, storage: BaseStorage) -> None:
        self._storage = storage
        self._books: list[Book] = []
        self.reload()

    def reload(self) -> None:
        raw_items = self._storage.load()
        self._books = [
            Book.from_dict(item, fallback_id=i)
            for i, item in enumerate(raw_items, start=1)
        ]

    def save(self) -> None:
        self._storage.save([book.to_dict() for book in self._books])

    def get_all(self, sort_by: str = "title") -> list[Book]:
        if sort_by == "author":
            return sorted(self._books, key=lambda b: b.author.lower())
        if sort_by == "year":
            return sorted(self._books, key=lambda b: (b.year is None, -(b.year or 0)))
        return sorted(self._books, key=lambda b: b.title.lower())

    def get_by_id(self, book_id: int) -> Book | None:
        return next((b for b in self._books if b.id == book_id), None)

    def get_genres(self) -> list[str]:
        return sorted({b.genre for b in self._books if b.genre}, key=str.lower)

    def search_by_title(self, query: str) -> list[Book]:
        needle = query.strip().lower()
        if not needle:
            raise ValueError("Введите текст для поиска по названию.")
        return [b for b in self._books if needle in b.title.lower()]

    def search_by_author(self, query: str) -> list[Book]:
        needle = query.strip().lower()
        if not needle:
            raise ValueError("Введите текст для поиска по автору.")
        return [b for b in self._books if needle in b.author.lower()]

    def filter_by_genre(self, genre: str) -> list[Book]:
        needle = genre.strip().lower()
        return [b for b in self._books if needle in b.genre.lower()]

    def add_book(
        self, title: str, author: str, genre: str, year: int | str | None = None, description: str = ""
    ) -> Book:
        next_id = max((b.id for b in self._books), default=0) + 1
        book = Book(next_id, title, author, genre, year, description)
        self._books.append(book)
        self.save()
        return book

    def update_book(self, book_id: int, field: str, value: str | None) -> Book:
        book = self.get_by_id(book_id)
        if book is None:
            raise ValueError(f"Книга с ID {book_id} не найдена.")

        if field == "title":
            book.title = value or ""
        elif field == "author":
            book.author = value or ""
        elif field == "genre":
            book.genre = value or ""
        elif field == "year":
            book.year = value
        elif field == "description":
            book.description = value
        else:
            raise ValueError("Неизвестное поле для редактирования.")

        self.save()
        return book