import logging
from thefuzz import process     #->fuzzywuzzy для обработки неточных соответствий
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext       #импорт библиотек для машины состояний
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from api import response_c_list, c_info
from coinmarketcap import coin_request
from crypt_most_hype import coin_request_hype



# Объект бота
bot = Bot(token='2008374333:AAE-HcREZx4eCUHCtu5-2TFF77gVdO4f9gQ', parse_mode=types.ParseMode.HTML)
# диспетчер бота
# добавил хранилище в диспетчер
dp = Dispatcher(bot, storage=MemoryStorage())

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# класс для машины состояний
class User_choise(StatesGroup):
    waiting_for_msfo = State()
    waiting_for_crypto = State()

# Функция на команду /start
@dp.message_handler(state='*', commands='start')
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("""
    Вас приветствует бот-помошник для инвесторов и биржевых спекулянтов. \n
    Чтобы получить последний отчёт компании МСФО/РСБУ нажмите <b>'/Отчёт'</b> и введите название компании.\n 
    Узнать по каким компаниям есть отчёты, нажмите <b>'/Список компаний'</b>\n
    Узнать курс криптовалюты в данный момент, нажмите <b>'/Криптовалюта'</b> и введите название криптовалюты.\n
    Узнать топ самых торгуемых криптовалют, нажмине <b>'/Топ активных'</b>
    """)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ['/Список компаний', '/Отчёт МСФО/РСБУ', '/Криптовалюта', '/Топ активных', '/Start']
    keyboard.add(buttons[0]).add(buttons[1]).add(buttons[2], buttons[3]).add(buttons[4])
    await message.answer('Воспользуйтесь кнопками-коммандами', reply_markup=keyboard)
    await state.finish()

# Функция на команду /Список_компаний
@dp.message_handler(state='*', commands='Список')
async def cmd_list(message: types.Message, state: FSMContext):
    await User_choise.waiting_for_msfo.set()
    await message.answer(",  ".join(response_c_list()))


# Функция на команду /Отчёт
@dp.message_handler(state='*', commands='Отчёт')
async def cmd_msfo(message: types.Message, state: FSMContext):
    await message.answer('Введите название компании: ')
    await User_choise.waiting_for_msfo.set()


# Функция на команду /Криптовалюта
@dp.message_handler(state='*', commands='Криптовалюта')
async def cmd_crypt(message: types.Message, state: FSMContext):
    await message.answer('Введите название криптовалюты целиком или тикер (только латинские символы): ')
    await User_choise.waiting_for_crypto.set()


# Функция на команду /Топ_активных
@dp.message_handler(state='*', commands='Топ')
async def cmd_crypt_hype(message: types.Message, state: FSMContext):
    await message.answer(coin_request_hype())
    await User_choise.waiting_for_crypto.set()


# Обработчик ввода названия криптовалюты
@dp.message_handler(content_types=['text'], state=User_choise.waiting_for_crypto)
async def cmd_crypt_answer(message: types.Message, state: FSMContext):
    await message.answer(f'<b>{coin_request(message.text)}</b>')

# Обработчик ожидающая пользовательский ввод на команду /Отчёт
@dp.message_handler(content_types=['text'], state=User_choise.waiting_for_msfo)
async def query_comp(message: types.Message, state: FSMContext):
# тут начинается корректировка неточного запроса пользователя
    company_name = process.extractOne(message.text, response_c_list())
# записываю в MemoryStorage переменную чтобы отправить в другой хэндлер
    async with state.proxy() as data:
        data['company_name'] = company_name[0]
# так как process.excractOne возвращает список, то получаем доступ к его значениям по индексам
    if company_name[1] >= 60:  #
        if company_name[1] < 99:
            markup_inline = types.InlineKeyboardMarkup()
            item_yes = types.InlineKeyboardButton(text='Да', callback_data='Yes')
            item_no = types.InlineKeyboardButton(text='Нет', callback_data='No')
            markup_inline.add(item_yes, item_no)
            await message.answer(f'Вы имели ввиду компанию {data["company_name"]}?', reply_markup=markup_inline)
        else:
            await response_data(message.answer)
    else:
        await message.answer('по вашему запросу нет информации')

#функция инлайновой клавиатуры с кнопками краткий отчёт и полный отчёт
async def response_data(user_msg):
    markup_inline = types.InlineKeyboardMarkup()
    item_short = types.InlineKeyboardButton(text='Краткий', callback_data='short')
    item_long = types.InlineKeyboardButton(text='Полный', callback_data='long')
    markup_inline.add(item_short, item_long)
    await user_msg('Какой отчёт нужен краткий или полный?', reply_markup=markup_inline)

# функция обработчик callback данных пользовательского выбора
@dp.callback_query_handler(text=['Yes','No','short','long'], state=User_choise.waiting_for_msfo)
async def callback_inline_menu(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'Yes':
        # если выбор "Да" то запускается функция с кнопками "краткий" и "полный"
        await bot.delete_message(call.from_user.id, call.message.message_id)  # удаляем кнопки после использования
        await response_data(call.message.answer)
    elif call.data == 'No':
        await bot.delete_message(call.from_user.id, call.message.message_id)
        await call.message.answer('Попробуйте ещё раз')
    elif call.data == 'short':
        result = await state.get_data()     #получаю переменную из state memory storage
        await call.message.answer(c_info(result['company_name'], 'short_info'))  # выдается краткий отчёт
    elif call.data == 'long':
        result = await state.get_data()     #получаю переменную из state memory storage
        await call.message.answer(c_info(result['company_name'], 'long_info'))  # выдается полный отчёт


# Запуск бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
