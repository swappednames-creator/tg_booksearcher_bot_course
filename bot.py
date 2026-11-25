import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from catalog import Book, BookCatalog, JsonStorage
from config import BOOKS_FILE, get_bot_token
from keyboards import cancel_kb, edit_fields_kb, genres_kb, main_menu_kb, pagination_kb, sort_kb

router = Router()
catalog: BookCatalog


class SearchState(StatesGroup):
    by_title = State()
    by_author = State()


class AddBookState(StatesGroup):
    title = State()
    author = State()
    genre = State()
    year = State()
    description = State()


class EditBookState(StatesGroup):
    book_id = State()
    new_value = State()


async def send_results(target: Message, state: FSMContext, books: list[Book], header: str) -> None:
    if not books:
        await target.answer("😕 Ничего не найдено.", reply_markup=main_menu_kb())
        return

    await state.update_data(result_ids=[b.id for b in books], header=header)
    text = f"{header} (найдено: {len(books)})\n\n{books[0].format_card()}"
    markup = pagination_kb(0, len(books)) if len(books) > 1 else None
    await target.answer(text, reply_markup=markup)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👋 Привет! Я бот для поиска книг.\nВыберите действие в меню ниже:",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Доступные возможности:</b>\n"
        "• Поиск по названию и автору\n"
        "• Фильтрация по жанрам\n"
        "• Просмотр всех книг с сортировкой\n"
        "• Добавление и редактирование записей"
    )


@router.message(F.text == "❌ Отмена")
@router.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb())


# --- Поиск по названию ---
@router.message(F.text == "🔍 По названию")
async def ask_title(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchState.by_title)
    await message.answer("Введите название книги (или его часть):", reply_markup=cancel_kb())


@router.message(SearchState.by_title)
async def handle_title_search(message: Message, state: FSMContext) -> None:
    try:
        books = catalog.search_by_title(message.text or "")
    except ValueError as err:
        await message.answer(f"⚠️ {err}")
        return

    await state.clear()
    await message.answer("Результаты поиска:", reply_markup=main_menu_kb())
    await send_results(message, state, books, f"🔍 Поиск: «{message.text.strip()}»")


# --- Поиск по автору ---
@router.message(F.text == "✍️ По автору")
async def ask_author(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchState.by_author)
    await message.answer("Введите имя или фамилию автора:", reply_markup=cancel_kb())


@router.message(SearchState.by_author)
async def handle_author_search(message: Message, state: FSMContext) -> None:
    try:
        books = catalog.search_by_author(message.text or "")
    except ValueError as err:
        await message.answer(f"⚠️ {err}")
        return

    await state.clear()
    await message.answer("Результаты поиска:", reply_markup=main_menu_kb())
    await send_results(message, state, books, f"✍️ Автор: «{message.text.strip()}»")


# --- Фильтр по жанру ---
@router.message(F.text == "🏷 По жанру")
async def show_genres(message: Message) -> None:
    genres = catalog.get_genres()
    if not genres:
        await message.answer("Каталог пока пуст.")
        return
    await message.answer("Выберите жанр:", reply_markup=genres_kb(genres))


@router.callback_query(F.data.startswith("genre:"))
async def handle_genre_choice(callback: CallbackQuery, state: FSMContext) -> None:
    genres = catalog.get_genres()
    idx = int(callback.data.split(":")[1])
    if idx >= len(genres):
        await callback.answer("Жанр не найден.", show_alert=True)
        return

    genre = genres[idx]
    books = catalog.filter_by_genre(genre)
    await callback.answer()
    if callback.message:
        await send_results(callback.message, state, books, f"🏷 Жанр: {genre}")


# --- Все книги и сортировка ---
@router.message(F.text == "📚 Все книги")
async def ask_sort(message: Message) -> None:
    await message.answer("Выберите способ сортировки:", reply_markup=sort_kb())


@router.callback_query(F.data.startswith("sort:"))
async def handle_sort(callback: CallbackQuery, state: FSMContext) -> None:
    sort_by = callback.data.split(":")[1]
    titles = {"title": "по названию", "author": "по автору", "year": "по году"}
    books = catalog.get_all(sort_by=sort_by)
    await callback.answer()
    if callback.message:
        await send_results(callback.message, state, books, f"📚 Все книги ({titles.get(sort_by, '')})")


# --- Листание страниц (пагинация) ---
@router.callback_query(F.data.startswith("page:"))
async def handle_page(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    ids: list[int] = data.get("result_ids", [])
    header: str = data.get("header", "📚 Книги")

    page = int(callback.data.split(":")[1])
    if not ids or not (0 <= page < len(ids)):
        await callback.answer("Список устарел, выполните поиск заново.", show_alert=True)
        return

    book = catalog.get_by_id(ids[page])
    if book is None or callback.message is None:
        await callback.answer("Книга не найдена.", show_alert=True)
        return

    text = f"{header} (найдено: {len(ids)})\n\n{book.format_card()}"
    await callback.message.edit_text(text, reply_markup=pagination_kb(page, len(ids)))
    await callback.answer()


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# --- Добавление книги ---
@router.message(F.text == "➕ Добавить книгу")
async def start_add_book(message: Message, state: FSMContext) -> None:
    await state.set_state(AddBookState.title)
    await message.answer("Введите название новой книги:", reply_markup=cancel_kb())


@router.message(AddBookState.title)
async def add_title(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ Название не может быть пустым. Попробуйте ещё раз:")
        return
    await state.update_data(title=text)
    await state.set_state(AddBookState.author)
    await message.answer("Введите автора книги:")


@router.message(AddBookState.author)
async def add_author(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ Имя автора не может быть пустым. Попробуйте ещё раз:")
        return
    await state.update_data(author=text)
    await state.set_state(AddBookState.genre)
    await message.answer("Введите жанр книги:")


@router.message(AddBookState.genre)
async def add_genre(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ Жанр не может быть пустым. Попробуйте ещё раз:")
        return
    await state.update_data(genre=text)
    await state.set_state(AddBookState.year)
    await message.answer("Введите год издания (или отправьте «-», чтобы пропустить):")


@router.message(AddBookState.year)
async def add_year(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    year = None if raw == "-" else raw
    if year is not None:
        try:
            Book(0, "test", "test", "test", year)
        except ValueError as err:
            await message.answer(f"⚠️ {err}\nВведите корректный год или «-»:")
            return
    await state.update_data(year=year)
    await state.set_state(AddBookState.description)
    await message.answer("Введите краткое описание (или «-», чтобы пропустить):")


@router.message(AddBookState.description)
async def add_description(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    description = "" if raw == "-" else raw
    data = await state.get_data()

    try:
        book = catalog.add_book(
            title=data["title"],
            author=data["author"],
            genre=data["genre"],
            year=data["year"],
            description=description,
        )
    except ValueError as err:
        await message.answer(f"⚠️ Ошибка: {err}", reply_markup=main_menu_kb())
        await state.clear()
        return

    await state.clear()
    await message.answer(f"✅ Книга добавлена и сохранена!\n\n{book.format_card()}", reply_markup=main_menu_kb())


# --- Редактирование книги ---
@router.message(F.text == "✏️ Изменить книгу")
async def start_edit_book(message: Message, state: FSMContext) -> None:
    await state.set_state(EditBookState.book_id)
    await message.answer("Введите ID книги, которую хотите изменить:", reply_markup=cancel_kb())


@router.message(EditBookState.book_id)
async def ask_edit_field(message: Message, state: FSMContext) -> None:
    try:
        book_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("⚠️ ID должен быть целым числом. Попробуйте ещё раз:")
        return

    book = catalog.get_by_id(book_id)
    if book is None:
        await message.answer("⚠️ Книга с таким ID не найдена. Введите другой ID:")
        return

    await state.clear()
    await message.answer(
        f"Найдена книга:\n\n{book.format_card()}\n\nЧто хотите изменить?",
        reply_markup=main_menu_kb(),
    )
    await message.answer("Выберите поле:", reply_markup=edit_fields_kb(book.id))


@router.callback_query(F.data.startswith("edit:"))
async def choose_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    _, raw_id, field = callback.data.split(":")
    await state.set_state(EditBookState.new_value)
    await state.update_data(edit_book_id=int(raw_id), edit_field=field)
    await callback.answer()
    if callback.message:
        await callback.message.answer("Введите новое значение:", reply_markup=cancel_kb())


@router.message(EditBookState.new_value)
async def save_edited_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    try:
        book = catalog.update_book(
            book_id=data["edit_book_id"],
            field=data["edit_field"],
            value=message.text,
        )
    except ValueError as err:
        await message.answer(f"⚠️ {err}\nВведите корректное значение:")
        return

    await state.clear()
    await message.answer(f"✅ Запись обновлена!\n\n{book.format_card()}", reply_markup=main_menu_kb())


@router.message()
async def fallback_message(message: Message) -> None:
    await message.answer("Пожалуйста, выберите действие с помощью кнопок меню.", reply_markup=main_menu_kb())


async def main() -> None:
    global catalog
    logging.basicConfig(level=logging.INFO)
    catalog = BookCatalog(JsonStorage(BOOKS_FILE))
    bot = Bot(
        token=get_bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())