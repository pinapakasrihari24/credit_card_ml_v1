#!/usr/bin/env python3
"""
Initialize Cloud SQL database with sample data.
Run this after Terraform infrastructure is created.
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

DATABASE_URL = os.environ.get('DATABASE_URL')
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sample')


def init_db():
    """Initialize database with schema and data."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Create tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id VARCHAR(50) PRIMARY KEY,
            credit_score INTEGER,
            age INTEGER,
            annual_income FLOAT,
            credit_limit FLOAT,
            risk_profile VARCHAR(20),
            account_age_days INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) REFERENCES user_profiles(user_id),
            timestamp TIMESTAMP,
            amount FLOAT,
            merchant_category VARCHAR(50),
            city VARCHAR(50),
            is_weekend BOOLEAN,
            hour_of_day INTEGER,
            day_of_month INTEGER,
            is_foreign BOOLEAN,
            is_fraudulent BOOLEAN
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_features (
            user_id VARCHAR(50) PRIMARY KEY REFERENCES user_profiles(user_id),
            tx_count INTEGER,
            total_spent FLOAT,
            avg_tx FLOAT,
            std_tx FLOAT,
            max_tx FLOAT,
            min_tx FLOAT,
            fraud_count INTEGER,
            tx_per_day FLOAT,
            spent_cash_advance FLOAT,
            spent_entertainment FLOAT,
            spent_gas_stations FLOAT,
            spent_groceries FLOAT,
            spent_healthcare FLOAT,
            spent_online_shopping FLOAT,
            spent_other FLOAT,
            spent_restaurants FLOAT,
            spent_travel FLOAT,
            spent_utilities FLOAT,
            avg_hour FLOAT,
            weekend_ratio FLOAT,
            utilization FLOAT,
            income_to_limit FLOAT
        )
    """)

    # Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_is_fraudulent ON transactions(is_fraudulent)")

    conn.commit()

    # Load CSV data
    profiles_df = pd.read_csv(os.path.join(DATA_PATH, 'sample_credit_card_profiles.csv'))
    tx_df = pd.read_csv(os.path.join(DATA_PATH, 'sample_credit_card_transactions.csv'))
    features_df = pd.read_csv(os.path.join(DATA_PATH, 'sample_credit_card_user_features.csv'))

    # Insert profiles
    for _, row in profiles_df.iterrows():
        cur.execute("""
            INSERT INTO user_profiles VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (user_id) DO NOTHING
        """, (row['user_id'], int(row['credit_score']), int(row['age']),
              float(row['annual_income']), float(row['credit_limit']),
              row['risk_profile'], int(row['account_age_days'])))

    # Insert transactions
    for _, row in tx_df.iterrows():
        cur.execute("""
            INSERT INTO transactions (user_id, timestamp, amount, merchant_category, city,
                                       is_weekend, hour_of_day, day_of_month, is_foreign, is_fraudulent)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (row['user_id'], row['timestamp'], float(row['amount']), row['merchant_category'],
              row['city'], row['is_weekend'], int(row['hour_of_day']), int(row['day_of_month']),
              row['is_foreign'], row['is_fraudulent']))

    # Insert features
    for _, row in features_df.iterrows():
        cur.execute(f"""
            INSERT INTO user_features VALUES ({','.join(['%s'] * 28)})
            ON CONFLICT (user_id) DO NOTHING
        """, (
            row['user_id'], int(row['tx_count']), float(row['total_spent']), float(row['avg_tx']),
            float(row['std_tx']), float(row['max_tx']), float(row['min_tx']), int(row['fraud_count']),
            float(row['tx_per_day']), float(row['spent_Cash_Advance']), float(row['spent_Entertainment']),
            float(row['spent_Gas_Stations']), float(row['spent_Groceries']), float(row['spent_Healthcare']),
            float(row['spent_Online_Shopping']), float(row['spent_Other']), float(row['spent_Restaurants']),
            float(row['spent_Travel']), float(row['spent_Utilities']), float(row['avg_hour']),
            float(row['weekend_ratio']), float(row['utilization']), float(row['income_to_limit'])
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("Database initialized successfully!")


if __name__ == '__main__':
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set")
        exit(1)
    init_db()
