import math
import asyncio
import aiohttp
import datetime
import io
from aiogram.types import BufferedInputFile
from aiogram import Router
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import numpy as np
import matplotlib.pyplot as plt
import bd_operations as db

with open("api.txt", 'r') as file:
    openweathermap_api_key = file.readline().rstrip()
    bot_api_key = file.readline().rstrip()

bot = Bot(token=bot_api_key)
dp = Dispatcher()

async def get_current_temperature(city_name, api_key):
  url = "http://api.openweathermap.org/data/2.5/weather"
  params = {
        'q': city_name,
        'appid': api_key,
        'units': 'metric'
  }
  try:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=10) as response:
            return await response.json()
  except Exception as e:
        return {"error": str(e), "cod": 500}


async def get_product_calories(product_name):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        'search_terms': product_name,
        'json': 1,
        'page_size': 1
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('products'):
                    product = data['products'][0]
                    calories = product.get('nutriments', {}).get('energy-kcal_100g')
                    
                    if calories:
                        return {
                            'name': product.get('product_name', product_name),
                            'calories_per_100g': calories
                        }
    
    except:
        pass
    
    return None


activities_list = {
    "ходьба": 3.5,
    "бег": 7.5,
    "бег трусцой": 7.0,
    "велосипед": 7.5,
    "плавание": 6.0,
    "йога": 3.0,
    "силовая тренировка": 6.0,
    "отжимания": 8.0,
    "приседания": 5.0,
    "скакалка": 10.0,
    "теннис": 7.0,
    "футбол": 8.0,
    "баскетбол": 8.0,
    "аэробика": 6.5,
    "пилатес": 3.5,
}


class Profile(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()
    calorie_goal = State()

class Product(StatesGroup):
    name = State()
    calories_100g = State()
    calories = State()

router = Router()
dp.include_router(router)


# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
/set_profile - Заполнить профиль
/show_profile - Показать данные профиля

/log_water [кол-во мл] - Записать выпитую воду
/log_food [название продукта] - Добавить съеденную еду
/log_workout [тип тренировки] [время в мин] - Записать тренировку

/check_progress - Текущий прогресс за день
/show_statistics - Графики за неделю/месяц/год

Типы тренировок:
ходьба, бег, велосипед, плавание, йога, 
силовая тренировка, отжимания, приседания, 
скакалка, теннис, футбол, баскетбол, 
аэробика, пилатес

Примеры использования:
/log_water 500
/log_food яблоко
/log_workout бег 30
    """
    await message.answer(help_text)

# Заполнение профиля
@dp.message(Command("set_profile"))
async def start_form(message: Message, state: FSMContext):
    await message.answer("""Привет!\nДля расчета суточной нормы калорий и нормы воды ответь на несколько вопросов:\nВес (в кг)""")
    await state.set_state(Profile.weight)

@dp.message(Profile.weight)
async def process_weight(message: Message, state: FSMContext):
    await state.update_data(weight=message.text)
    await message.answer("Рост (в см)")
    await state.set_state(Profile.height)

@dp.message(Profile.height)
async def process_height(message: Message, state: FSMContext):
    await state.update_data(height=message.text)
    await message.answer("Возраст")
    await state.set_state(Profile.age)

@dp.message(Profile.age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Уровень активности (мин/день)")
    await state.set_state(Profile.activity)

@dp.message(Profile.activity)
async def process_activity(message: Message, state: FSMContext):
    await state.update_data(activity=message.text)
    await message.answer("Город")
    await state.set_state(Profile.city)

def water_norm_calc(weight, activity, temperature=0):
    """
    Базовая норма=Вес×30мл/кг 
    +500мл  за каждые 30 минут активности.
    +500−1000мл  за жаркую погоду (> 25°C)
    """

    norm = weight*30 + 500*(int(activity)//30)
    if temperature > 25:
       norm += 750

    return math.ceil(norm / 100) * 100

def calories_norm_calc(weight, height, age, activity):
    """
    Норма калорий:
    Калории=10*Вес (кг)+6.25*Рост (см)-5*Возраст 
    + (минуты активности / 30) * 300 ккал
    """

    norm = 10*weight + 6.25*height - 5*age + (activity // 30)*300
    return math.ceil(norm / 100) * 100

# Завершение заполнения профиля и сохранение данных в БД
@dp.message(Profile.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()

    weight = data.get("weight")
    height = data.get("height")
    age = data.get("age")
    activity = data.get("activity")
    city = data.get("city")

    water_norm = water_norm_calc(float(weight), float(activity))
    calories_norm = calories_norm_calc(float(weight), float(height), int(age), int(activity))

    db.save_profiles_data(message.from_user.id, {
        'weight': weight,
        'height': height,
        'age': age,
        'activity': activity,
        'city': city,
        'water_norm': water_norm,
        'calories_norm': calories_norm
    })

    await message.answer(
        f"Данные сохранены:\n"
        f"Вес: {weight} кг\n"
        f"Рост: {height} см\n"
        f"Возраст: {age} лет\n"
        f"Активность: {activity} мин/день\n"
        f"Город: {city}\n\n"
        f"Средняя норма воды в сутки: {water_norm} мл\n"
        f"Средняя норма калорий в сутки: {calories_norm} ккал"
    )   
    await state.clear()

@dp.message(Command("show_profile"))
async def cmd_show_profile(message: Message):
    try:
        data = db.get_profiles_data(message.from_user.id)
        await message.answer(
            f"Данные пользователя:\n"
            f"Вес: {data['weight']} кг\n"
            f"Рост: {data['height']} см\n"
            f"Возраст: {data['age']}\n"
            f"Уровень активности: {data['activity']} мин/день\n\n"
            f"Город: {data['city']}\n"
            f"Норма воды: {data['water_norm']}\n"
            f"Норма калорий: {data['calories_norm']}\n"
            )
    except:
        await message.answer('По твоему профилю пока что нет данных\nИспользуй /set_profile')


@dp.message(Command("test"))
async def cmd_test(message: Message):
    try:
        data = db.get_profiles_data(message.from_user.id)
        city = data['city']
        water_norm = water_norm_calc(data['weight'], data['activity'])
        await message.answer(f'{water_norm}')
        await message.answer(f'{city}')

        weather_info = await get_current_temperature(city, openweathermap_api_key)
        curr_temp = weather_info.get('main').get('temp')
        await message.answer(f'{curr_temp}')

        water_norm = water_norm_calc(data['weight'], data['activity'], curr_temp)
        await message.answer(f'{water_norm}')

        calories_norm = calories_norm_calc(data['weight'], data['height'], data['age'], data['activity'])
        await message.answer(f'{calories_norm}')


    except:
        await message.answer('По твоему профилю пока что нет данных\nИспользуй /set_profile')


@dp.message(Command("log_water"))
async def log_water(message: Message):
    try:
        user_id = message.from_user.id
        date = datetime.date.today()
        water_delta = int(message.text.split(' ')[1])
        db.log_water(user_id, date, water_delta)
        await message.answer('Данные сохранены!')
    except:
        await message.answer('По твоему профилю пока что нет данных\nИспользуй /set_profile')


@dp.message(Command("log_food"))
async def start_food_form(message: Message, state: FSMContext):
    product_name = message.text.split(' ')[1]
    product_data = await get_product_calories(product_name)
    calories_100g = int(product_data['calories_per_100g'])
    await state.update_data(product_name=product_name, calories_100g=calories_100g)
    await message.answer(
        f"{product_name} - {calories_100g} ккал на 100 г.\n"
        "Сколько грамм вы съели?"
        )
    await state.set_state(Product.calories)

@dp.message(Product.calories)
async def product_calories(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        date = datetime.date.today()
        data = await state.get_data()
        calories_100g = data['calories_100g']
        calories = math.ceil(int(message.text) * calories_100g/100)
        db.log_food(user_id, date, calories)
        await message.answer(f"Записано: {calories} ккал")
    except:
        await message.answer('По твоему профилю пока что нет данных\nИспользуй /set_profile')
        await state.clear()


@dp.message(Command("log_workout"))
async def log_workout(message: Message):
    try:
        user_id = message.from_user.id
        date = datetime.date.today()
        activity_type = message.text.split(' ')[1]
        activity_time = int(message.text.split(' ')[2])
        data = db.get_profiles_data(message.from_user.id)
        kkal_delta = math.ceil(activities_list[activity_type] * data['weight'] * activity_time / 60)
        add_water = math.ceil(activity_time / 30)*200

        db.log_workout(user_id, date, kkal_delta, add_water)
        
        await message.answer(f"{activity_type} {activity_time} минут — {kkal_delta} ккал\n"
                             f"Дополнительно: выпейте {add_water} мл воды.")
    except KeyError: 
        activities_text = "\n".join([f" - {activity}" for activity in activities_list.keys()])
        await message.answer(
            "Данный тип тренировки пока что не поддерживается\n"
            "Выберите вариант из предложенного списка:\n"
            f"{activities_text}"
        )
        return 
    except:
        await message.answer('По твоему профилю пока что нет данных\nИспользуй /set_profile')



@dp.message(Command("check_progress"))
async def check_progress(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        date = datetime.date.today()
        data = db.get_daily_statistics(user_id, date)
        todo_water = max(data['water_norm'] - data['water_as_is'], 0)
        balance = data['calories_consumed'] - data['calories_burned']

        await message.answer("Вода:\n"
                             f"- Выпито: {data['water_as_is']} мл из {data['water_norm']} мл\n"
                             f"- Осталось: {todo_water} мл\n\n"
                             "Калории:\n"
                             f"- Потреблено: {data['calories_consumed']} ккал из {data['calories_norm']} ккал\n"
                             f"- Сожжено: {data['calories_burned']} ккал\n"
                             f"- Баланс: {balance} ккал\n"
                             )
    except:
        await message.answer('По твоему профилю пока что нет данных\nИспользуй /set_profile')



@router.message(Command("show_statistics"))
async def show_keyboard(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="За неделю", callback_data="btn_week")],
            [InlineKeyboardButton(text="За месяц", callback_data="btn_month")],
            [InlineKeyboardButton(text="За год", callback_data="btn_year")],
        ]
    )
    await message.answer("Выберите опцию:", reply_markup=keyboard)


def plot_stats(df, period='week'):
    if df.empty:
        return None
    
    # Создаем график
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    if period == 'year':
        dates = df['month'].dt.strftime('%b')
        water = df['avg_water']
        water_norm = df['avg_water_norm']
        calories_cons = df['avg_calories_consumed']
        calories_burn = df['avg_calories_burned']
        calories_norm = df['avg_calories_norm']
    else:
        df = df.sort_values('date')
        dates = df['date'].dt.strftime('%d.%m')
        water = df['water_as_is']
        water_norm = df['water_norm']
        calories_cons = df['calories_consumed']
        calories_burn = df['calories_burned']
        calories_norm = df['calories_norm']
    
    # Вода
    ax1.bar(dates, water, color='skyblue', label='Выпито')
    ax1.plot(dates, water_norm, 'b--', label='Норма', marker='o')
    ax1.set_title('Вода')
    ax1.set_ylabel('Мл')
    ax1.legend()
    
    # Калории
    x = np.arange(len(dates))
    width = 0.35
    
    ax2.bar(x - width/2, calories_cons, width, color='lightgreen', label='Потреблено')
    ax2.bar(x + width/2, calories_burn, width, color='lightcoral', label='Сожжено')
    ax2.plot(x, calories_norm, 'r--', label='Норма', marker='o')
    ax2.set_title('Калории')
    ax2.set_ylabel('Ккал')
    ax2.set_xticks(x)
    ax2.set_xticklabels(dates)
    ax2.legend()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    return BufferedInputFile(buf.getvalue(), filename='graph.png')


@router.callback_query()
async def handle_callback(callback_query):
    user_id = callback_query.from_user.id
    photo = None
    
    if callback_query.data == "btn_week":
        df = db.get_week_data(user_id)
        photo = plot_stats(df, 'week')
        await callback_query.message.answer_photo(photo=photo, caption="Статистика за неделю")
    elif callback_query.data == "btn_month":
        df = db.get_month_data(user_id)
        photo = plot_stats(df, 'month')
        await callback_query.message.answer_photo(photo=photo, caption="Статистика за месяц")
    elif callback_query.data == "btn_year":
        df = db.get_year_data(user_id)
        photo = plot_stats(df, 'year')
        await callback_query.message.answer_photo(photo=photo, caption="Статистика за год")


# Основная функция запуска бота
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())