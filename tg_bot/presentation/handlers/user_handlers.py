from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from application.services.gemini_service import GeminiService, IntentResult
from application.services.search_service import SearchService
from application.services.user_service import UserService
from core.logger import get_logger
from domain.entities.product import Product

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

router = Router(name="user_handlers")


class SearchStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_budget = State()


def _format_product(product: Product, index: int) -> str:
    parts = [f"<b>{index}. {product.short_title}</b>"]
    parts.append(f"💰 <b>{product.formatted_price}</b>")
    if product.rating:
        stars = "⭐" * round(product.rating)
        reviews = f" ({product.reviews_count} отзывов)" if product.reviews_count else ""
        parts.append(f"{stars}{reviews}")
    if product.seller:
        parts.append(f"🏪 {product.seller}")
    parts.append(f'<a href="{product.url}">🔗 Открыть на Kaspi</a>')
    return "\n".join(parts)


def _build_results_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="new_search")],
        [InlineKeyboardButton(text="🗑 Очистить историю чата", callback_data="clear_history")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_start_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔍 Найти товар", callback_data="new_search")],
        [InlineKeyboardButton(text="💬 Чат с AI", callback_data="open_chat")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def handle_start(message: Message, user_service: UserService) -> None:
    tg_user = message.from_user
    if tg_user is None:
        return

    user, created = await user_service.get_or_register(tg_user)

    greeting = (
        f"👋 Добро пожаловать, <b>{user.first_name}</b>!\n\n"
        f"Я помогу найти лучшие товары на Kaspi.kz.\n"
        f"Просто напиши, что ищешь — и я найду лучшие варианты!"
    ) if created else (
        f"👋 С возвращением, <b>{user.first_name}</b>!\n\n"
        f"Что будем искать сегодня?"
    )

    await message.answer(
        greeting,
        parse_mode="HTML",
        reply_markup=_build_start_keyboard(),
    )
    logger.info("handler.start", telegram_id=user.telegram_id, is_new=created)


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    text = (
        "📖 <b>Как пользоваться ботом:</b>\n\n"
        "1. Напишите название товара\n"
        "2. Укажите бюджет, если нужно\n"
        "3. Получите список предложений с Kaspi.kz\n\n"
        "<b>Примеры запросов:</b>\n"
        "• «Найди телефон Samsung до 150 000 тенге»\n"
        "• «Хочу наушники AirPods»\n"
        "• «Ноутбук для работы, бюджет 200000»\n\n"
        "<b>Команды:</b>\n"
        "/start — главное меню\n"
        "/search — начать поиск\n"
        "/chat — AI-ассистент\n"
        "/clear — очистить историю\n"
        "/help — эта справка"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("search"))
@router.callback_query(F.data == "new_search")
async def handle_search_start(event: Message | CallbackQuery, state: FSMContext) -> None:
    text = (
        "🔍 <b>Поиск товаров на Kaspi.kz</b>\n\n"
        "Напишите, что ищете. Можно указать бюджет прямо в запросе:\n"
        "<i>«Samsung Galaxy до 200000 тенге»</i>"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, parse_mode="HTML")
    else:
        await event.answer(text, parse_mode="HTML")

    await state.set_state(SearchStates.waiting_for_query)


@router.message(Command("chat"))
@router.callback_query(F.data == "open_chat")
async def handle_chat_start(event: Message | CallbackQuery, state: FSMContext) -> None:
    text = (
        "💬 <b>AI-ассистент активирован</b>\n\n"
        "Задайте любой вопрос о товарах или попросите помочь с выбором.\n"
        "Для выхода — /start"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, parse_mode="HTML")
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(Command("clear"))
@router.callback_query(F.data == "clear_history")
async def handle_clear_history(
    event: Message | CallbackQuery,
    gemini_service: GeminiService,
) -> None:
    telegram_id = (
        event.from_user.id if event.from_user else None
    )
    if telegram_id:
        await gemini_service.clear_history(telegram_id)

    text = "🗑 История диалога очищена."
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text)
    else:
        await event.answer(text)


@router.message(SearchStates.waiting_for_query)
async def handle_search_query(
    message: Message,
    state: FSMContext,
    gemini_service: GeminiService,
    search_service: SearchService,
) -> None:
    if not message.text or not message.from_user:
        return

    thinking_msg = await message.answer("🔍 Анализирую запрос...")

    try:
        intent: IntentResult = await gemini_service.extract_intent(
            telegram_id=message.from_user.id,
            user_message=message.text,
        )

        logger.info(
            "handler.search_query",
            telegram_id=message.from_user.id,
            query=intent.query,
            budget=intent.budget,
        )

        await thinking_msg.edit_text("⏳ Ищу товары на Kaspi.kz...")

        products = await search_service.search(
            query=intent.query,
            budget=float(intent.budget) if intent.budget else None,
        )

        if not products:
            await thinking_msg.edit_text(
                "😕 По вашему запросу ничего не найдено.\n\n"
                "Попробуйте:\n"
                "• Уточнить название товара\n"
                "• Увеличить бюджет\n"
                "• Использовать другие ключевые слова",
            )
            return

        header = (
            f"✅ Найдено <b>{len(products)}</b> предложений"
            f"{f' в бюджете до <b>{intent.budget:,} ₸</b>' if intent.budget else ''}"
            f" по запросу «{intent.query}»:\n\n"
        )

        result_blocks = [_format_product(p, i + 1) for i, p in enumerate(products[:5])]
        full_text = header + "\n\n".join(result_blocks)

        await thinking_msg.edit_text(
            full_text,
            parse_mode="HTML",
            reply_markup=_build_results_keyboard(products),
            disable_web_page_preview=True,
        )

    except Exception as exc:
        logger.error("handler.search_error", error=str(exc))
        await thinking_msg.edit_text(
            "⚠️ Произошла ошибка при поиске. Попробуйте ещё раз."
        )
    finally:
        await state.clear()


@router.message(F.text)
async def handle_free_text(
    message: Message,
    gemini_service: GeminiService,
    state: FSMContext,
) -> None:
    if not message.text or not message.from_user:
        return

    current_state = await state.get_state()
    if current_state is not None:
        return

    typing_task = asyncio.create_task(
        _send_typing_action(message)
    )

    try:
        response = await gemini_service.chat(
            telegram_id=message.from_user.id,
            user_message=message.text,
        )
        typing_task.cancel()
        await message.answer(response, parse_mode="HTML")
    except Exception as exc:
        typing_task.cancel()
        logger.error("handler.free_text_error", error=str(exc))
        await message.answer("⚠️ Ошибка. Попробуйте ещё раз.")


async def _send_typing_action(message: Message) -> None:
    try:
        while True:
            await message.bot.send_chat_action(
                chat_id=message.chat.id,
                action="typing",
            )
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
