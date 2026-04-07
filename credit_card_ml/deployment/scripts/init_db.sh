#!/bin/bash
set -e

echo "Initializing Credit Card Fraud Detection database..."

# Database connection
export DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:password@localhost:5432/creditcard"}

# Create tables
psql "$DATABASE_URL" << 'EOF'
-- Create tables
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(50) PRIMARY KEY,
    credit_score INTEGER,
    age INTEGER,
    annual_income FLOAT,
    credit_limit FLOAT,
    risk_profile VARCHAR(20),
    account_age_days INTEGER
);

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
);

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
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_is_fraudulent ON transactions(is_fraudulent);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);

-- Copy data from CSV files
\copy user_profiles FROM 'data/sample/sample_credit_card_profiles.csv' CSV HEADER;
\copy transactions FROM 'data/sample/sample_credit_card_transactions.csv' CSV HEADER;
\copy user_features FROM 'data/sample/sample_credit_card_user_features.csv' CSV HEADER;

SELECT 'Database initialized successfully!' as status;
EOF

echo "Done!"
