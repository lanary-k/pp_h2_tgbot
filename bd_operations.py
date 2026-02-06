import sqlite3
import math
import datetime
import pandas as pd

# Инициализация БД
def init_db():
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            weight REAL,
            height REAL,
            age INTEGER,
            activity INTEGER,
            city VARCHAR(50),
            water_norm INTEGER,
            calories_norm INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_statistics (
            user_id INTEGER,
            date DATE,
            water_as_is INTEGER,
            calories_burned INTEGER,
            calories_consumed INTEGER,
            water_norm INTEGER,
            calories_norm INTEGER,
            PRIMARY KEY (user_id, date)
        )
    ''')

    connection.commit()
    connection.close()

# Сохранить данных пользователя в БД
def save_profiles_data(user_id, data):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO profiles 
        (user_id, weight, height, age, activity, city, water_norm, calories_norm) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (user_id, data['weight'], data['height'], data['age'], data['activity'], data['city'], data['water_norm'], data['calories_norm'])
    )
    
    connection.commit()
    connection.close()

# Показать данные пользователя
def get_profiles_data(user_id):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()
    
    cursor.execute('''
        SELECT weight, height, age, activity, city, water_norm, calories_norm FROM profiles 
        WHERE user_id = ?
        ''',
        (user_id,)
    )
    data = cursor.fetchone()
    
    connection.commit()
    connection.close()

    if data:
        columns = ['weight', 'height', 'age', 'activity', 'city']
        return dict(zip(columns, data))
    else:
        return None

def init_daily_statistics_by_user(user_id, date):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('''
        SELECT water_norm, calories_norm FROM profiles
        WHERE user_id = ?
        ''',
        (user_id, )
    )
    data = cursor.fetchone()
    water_norm = data[0]
    calories_norm = data[1]


    cursor.execute('''
            insert into daily_statistics
            (user_id, date, water_as_is, calories_burned, calories_consumed, water_norm, calories_norm) 
            VALUES (?, ?, 0, 0, 0, ?, ?)
            ''',
            (user_id, date, water_norm, calories_norm)
    )

    connection.commit()
    connection.close()

def log_water(user_id, date, water_delta):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('''
        SELECT * FROM daily_statistics
        WHERE user_id = ? and date = ?
        ''',
        (user_id, date, )
    )
    data = cursor.fetchone()

    if data is None:
        init_daily_statistics_by_user(user_id, date)
    
    cursor.execute('''
        SELECT water_as_is FROM daily_statistics
        WHERE user_id = ? and date = ?
        ''',
        (user_id, date, )
    )
    water_as_is = cursor.fetchone()[0]

    cursor.execute('''
        UPDATE daily_statistics
        SET water_as_is = ? + ?
        WHERE user_id = ? and date = ?
        ''',
        (water_as_is, water_delta, user_id, date, )
    )

    connection.commit()
    connection.close()


def log_food(user_id, date, food_delta):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()
    
    cursor.execute('''
        SELECT * FROM daily_statistics
        WHERE user_id = ? and date = ?
        ''',
        (user_id, date, )
    )
    data = cursor.fetchone()

    if data is None:
        init_daily_statistics_by_user(user_id, date)
    
    cursor.execute('''
        SELECT calories_consumed FROM daily_statistics
        WHERE user_id = ? and date = ?
        ''',
        (user_id, date, )
    )
    calories_consumed = cursor.fetchone()[0]

    cursor.execute('''
        UPDATE daily_statistics
        SET calories_consumed = ? + ?
        WHERE user_id = ? and date = ?
        ''',
        (calories_consumed, food_delta, user_id, date, )
    )

    connection.commit()
    connection.close()


def log_workout(user_id, date, kkal_delta, add_water):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()
    
    cursor.execute('''
        SELECT * FROM daily_statistics
        WHERE user_id = ? and date = ?
        ''',
        (user_id, date, )
    )
    data = cursor.fetchone()

    if data is None:
        init_daily_statistics_by_user(user_id, date)

    # обновление затраченных калорий
    cursor.execute('''
        SELECT calories_burned FROM daily_statistics
        WHERE user_id = ? and date = ?
        ''',
        (user_id, date, )
    )
    calories_burned = cursor.fetchone()[0]

    cursor.execute('''
        UPDATE daily_statistics
        SET calories_burned = ? + ?
        WHERE user_id = ? and date = ?
        ''',
        (calories_burned, kkal_delta, user_id, date, )
    )

    # обновление нормы воды за день
    cursor.execute('''
        SELECT water_norm FROM daily_statistics
        WHERE user_id = ? and date = ?
        ''',
        (user_id, date, )
    )
    water_norm = cursor.fetchone()[0]

    cursor.execute('''
        UPDATE daily_statistics
        SET water_norm = ? + ?
        WHERE user_id = ? and date = ?
        ''',
        (water_norm, add_water, user_id, date, )
    )

    connection.commit()
    connection.close()


def get_daily_statistics(user_id, date):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('''
        SELECT 
            water_as_is,
            calories_burned,
            calories_consumed,
            water_norm,
            calories_norm
        FROM daily_statistics
        WHERE user_id = ? and date = ?
        ''',
        (user_id, date, )
    )
    data = cursor.fetchone()

    connection.commit()
    connection.close()

    if data:
        columns = ['water_as_is', 'calories_burned', 'calories_consumed', 'water_norm', 'calories_norm']
        return dict(zip(columns, data))
    else:
        return None
  

def get_week_data(user_id):
    connection = sqlite3.connect('users.db')
    
    query = '''
        SELECT *
        FROM daily_statistics
        WHERE user_id = ? and 
              date >= date('now', '-7 days') and date <= date('now')
        ORDER BY date
    '''
    
    df = pd.read_sql_query(query, connection, params=(user_id,))
    connection.close()
    
    if not df.empty and 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    return df


def get_month_data(user_id):
    connection = sqlite3.connect('users.db')
    
    query = '''
        SELECT *
        FROM daily_statistics
        WHERE user_id = ? and 
              strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        ORDER BY date
    '''
    
    df = pd.read_sql_query(query, connection, params=(user_id,))
    connection.close()
    
    if not df.empty and 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    return df


def get_year_data(user_id):
    connection = sqlite3.connect('users.db')
    
    query = '''
        SELECT 
            strftime('%Y-%m', date) as month,
            AVG(water_as_is) as avg_water,
            AVG(calories_consumed) as avg_calories_consumed,
            AVG(calories_burned) as avg_calories_burned,
            AVG(water_norm) as avg_water_norm,
            AVG(calories_norm) as avg_calories_norm
        FROM daily_statistics
        WHERE user_id = ? 
            AND date >= date('now', '-1 year')
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    '''
    
    df = pd.read_sql_query(query, connection, params=(user_id,))
    connection.close()
    
    if not df.empty:
        df['month'] = pd.to_datetime(df['month'] + '-01')
    
    return df

init_db()