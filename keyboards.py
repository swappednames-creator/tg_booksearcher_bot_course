from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 По названию"), KeyboardButton(text="✍️ По автору")],
            [KeyboardButton(text="🏷 По жанру"), KeyboardButton(text="📚 Все книги")],
            [KeyboardButton(text="➕ Добавить книгу"), KeyboardButton(text="✏️ Изменить книгу")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def genres_kb(genres: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(genres), 2):
        row = [
            InlineKeyboardButton(text=genres[j], callback_data=f"genre:{j}")
            for j in range(i, min(i + 2, len(genres)))
        ]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sort_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="По названию", callback_data="sort:title"),
                InlineKeyboardButton(text="По автору", callback_data="sort:author"),
                InlineKeyboardButton(text="По году", callback_data="sort:year"),
            ]
        ]
    )


def pagination_kb(page: int, total: int) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{page - 1}"))
    buttons.append(InlineKeyboardButton(text=f"{page + 1} / {total}", callback_data="noop"))
    if page < total - 1:
        buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page:{page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def edit_fields_kb(book_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Название", callback_data=f"edit:{book_id}:title"),
                InlineKeyboardButton(text="Автор", callback_data=f"edit:{book_id}:author"),
            ],
            [
                InlineKeyboardButton(text="Жанр", callback_data=f"edit:{book_id}:genre"),
                InlineKeyboardButton(text="Год", callback_data=f"edit:{book_id}:year"),
            ],
            [InlineKeyboardButton(text="Описание", callback_data=f"edit:{book_id}:description")],
        ]
    )