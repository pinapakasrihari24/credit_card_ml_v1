"""
Credit Card User Behavior Data Generator - Optimized Version
Generates large synthetic datasets for ML tasks using vectorized operations.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)

NUM_USERS = 100_000
TRANSACTIONS_PER_USER = 200  # Average transactions per user

# Merchant categories with weights
CATEGORIES = ['Groceries', 'Restaurants', 'Gas Stations', 'Online Shopping',
              'Entertainment', 'Healthcare', 'Travel', 'Utilities', 'Cash Advance', 'Other']
CATEGORY_WEIGHTS = [0.25, 0.18, 0.12, 0.15, 0.08, 0.05, 0.06, 0.07, 0.02, 0.02]
CATEGORY_MEANS = [75, 35, 50, 120, 65, 150, 450, 180, 200, 55]
CATEGORY_STDS = [45, 25, 30, 180, 55, 200, 350, 80, 150, 40]

# Risk profiles
RISK_PROFILES = {
    'low': {'fraud_prob': 0.002, 'limit_range': (5000, 25000), 'weight': 0.70},
    'medium': {'fraud_prob': 0.015, 'limit_range': (25000, 75000), 'weight': 0.25},
    'high': {'fraud_prob': 0.08, 'limit_range': (75000, 150000), 'weight': 0.05},
}


def generate_profiles(n_users):
    """Generate user profiles."""
    user_ids = np.array([f"USER_{i:08d}" for i in range(n_users)])

    credit_scores = np.random.normal(700, 100, n_users).clip(300, 850).astype(int)
    ages = np.random.normal(42, 12, n_users).clip(18, 80).astype(int)
    incomes = np.exp(np.random.normal(10.5, 0.8, n_users)).clip(20000, 500000).astype(int)

    risk_keys = list(RISK_PROFILES.keys())
    risk_weights = [RISK_PROFILES[k]['weight'] for k in risk_keys]
    risk_profiles = np.random.choice(risk_keys, n_users, p=risk_weights)

    credit_limits = np.array([
        np.random.uniform(*RISK_PROFILES[r]['limit_range'])
        for r in risk_profiles
    ]).astype(int)

    account_ages = np.random.randint(30, 3650, n_users)

    return pd.DataFrame({
        'user_id': user_ids,
        'credit_score': credit_scores,
        'age': ages,
        'annual_income': incomes,
        'credit_limit': credit_limits,
        'risk_profile': risk_profiles,
        'account_age_days': account_ages,
    })


def generate_transactions(profiles_df, tx_per_user=200):
    """Generate transactions using vectorized operations."""
    n_users = len(profiles_df)
    n_tx = n_users * tx_per_user

    # User indices repeated for each transaction
    user_indices = np.repeat(np.arange(n_users), tx_per_user)
    user_ids = profiles_df['user_id'].iloc[user_indices].values

    # Risk profile per transaction
    risk_per_tx = profiles_df['risk_profile'].iloc[user_indices].values

    # Fraud probability per transaction (based on user's risk profile)
    fraud_mask = np.array([
        random.random() < RISK_PROFILES[r]['fraud_prob']
        for r in risk_per_tx
    ])

    # Timestamps: random over past year
    days_offset = np.random.randint(0, 365, n_tx)
    hours = np.random.normal(14, 4, n_tx).astype(int) % 24
    minutes = np.random.randint(0, 60, n_tx)
    timestamps = [
        datetime.now() - timedelta(days=int(d), hours=int(h), minutes=int(m))
        for d, h, m in zip(days_offset, hours, minutes)
    ]

    # Categories
    categories = np.random.choice(CATEGORIES, n_tx, p=CATEGORY_WEIGHTS)

    # Amounts - base distribution
    amounts = np.array([
        max(1, min(10000, np.random.lognormal(np.log(CATEGORY_MEANS[CATEGORIES.index(c)]), 0.5)))
        for c in categories
    ])

    # Scale up amounts for fraudulent users
    scale_factor = np.where(fraud_mask & (categories != 'Cash Advance'), 2.5, 1.0)
    scale_factor = np.where(fraud_mask & (categories == 'Cash Advance'), 3.0, scale_factor)
    amounts = amounts * scale_factor

    # Mark fraudulent transactions
    is_fraudulent = fraud_mask & (np.random.random(n_tx) < 0.3)

    # Other features
    cities = np.random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston',
                              'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego',
                              'Dallas', 'San Jose', 'Other'], n_tx)

    is_weekend = np.array([t.weekday() >= 5 for t in timestamps])
    hours_of_day = np.array([t.hour for t in timestamps])
    days_of_month = np.array([t.day for t in timestamps])

    return pd.DataFrame({
        'user_id': user_ids,
        'timestamp': timestamps,
        'amount': np.round(amounts, 2),
        'merchant_category': categories,
        'city': cities,
        'is_weekend': is_weekend,
        'hour_of_day': hours_of_day,
        'day_of_month': days_of_month,
        'is_foreign': np.random.random(n_tx) < 0.1,
        'is_fraudulent': is_fraudulent,
    })


def compute_user_features(profiles_df, transactions_df):
    """Compute aggregated behavioral features per user."""
    # Basic transaction stats
    tx_stats = transactions_df.groupby('user_id').agg(
        tx_count=('amount', 'count'),
        total_spent=('amount', 'sum'),
        avg_tx=('amount', 'mean'),
        std_tx=('amount', 'std'),
        max_tx=('amount', 'max'),
        min_tx=('amount', 'min'),
        fraud_count=('is_fraudulent', 'sum'),
        first_tx=('timestamp', 'min'),
        last_tx=('timestamp', 'max'),
    ).reset_index()

    tx_stats['tx_per_day'] = tx_stats['tx_count'] / (
        (tx_stats['last_tx'] - tx_stats['first_tx']).dt.days + 1
    )

    # Category spending
    category_pivot = transactions_df.pivot_table(
        index='user_id',
        columns='merchant_category',
        values='amount',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    category_pivot.columns = ['user_id'] + [f'spent_{c.replace(" ", "_")}' for c in category_pivot.columns[1:]]

    # Time patterns
    time_stats = transactions_df.groupby('user_id').agg(
        avg_hour=('hour_of_day', 'mean'),
        weekend_ratio=('is_weekend', 'mean'),
    ).reset_index()

    # Merge all
    features = profiles_df.merge(tx_stats, on='user_id', how='left')
    features = features.merge(category_pivot, on='user_id', how='left')
    features = features.merge(time_stats, on='user_id', how='left')

    # Derived features
    features['utilization'] = features['total_spent'] / features['credit_limit']
    features['income_to_limit'] = features['annual_income'] / features['credit_limit']

    features = features.drop(columns=['first_tx', 'last_tx'])
    features = features.fillna(0)

    return features


def generate_sample(sample_size=100, tx_per_user=20):
    """Generate small sample dataset for testing."""
    print(f"Generating sample: {sample_size} users, {tx_per_user} tx/user...")

    profiles = generate_profiles(sample_size)
    transactions = generate_transactions(profiles, tx_per_user)
    features = compute_user_features(profiles, transactions)

    return profiles, transactions, features


if __name__ == "__main__":
    print("=" * 60)
    print("CREDIT CARD USER BEHAVIOR DATA GENERATOR")
    print("=" * 60)

    print("\n[1/3] Generating user profiles...")
    profiles = generate_profiles(NUM_USERS)
    print(f"      Created {len(profiles):,} profiles")

    print("\n[2/3] Generating transactions...")
    transactions = generate_transactions(profiles, tx_per_user=TRANSACTIONS_PER_USER)
    print(f"      Created {len(transactions):,} transactions")
    print(f"      Fraud rate: {transactions['is_fraudulent'].mean()*100:.2f}%")

    print("\n[3/3] Computing user features...")
    features = compute_user_features(profiles, transactions)
    print(f"      Created {len(features):,} feature records")

    print("\n[Saving] Writing CSV files...")
    profiles.to_csv("credit_card_profiles.csv", index=False)
    transactions.to_csv("credit_card_transactions.csv", index=False)
    features.to_csv("credit_card_user_features.csv", index=False)

    print("\n" + "=" * 60)
    print("OUTPUT FILES")
    print("=" * 60)
    print(f"  - credit_card_profiles.csv      ({len(profiles):,} records)")
    print(f"  - credit_card_transactions.csv ({len(transactions):,} records)")
    print(f"  - credit_card_user_features.csv ({len(features):,} records)")

    print("\n" + "=" * 60)
    print("SAMPLE DATA")
    print("=" * 60)
    print("\nProfile columns:", list(profiles.columns))
    print("\nTransaction columns:", list(transactions.columns))
    print("\nFeature columns:", list(features.columns))
    print(f"\nFeature dimensions: {features.shape[1] - 1} features per user")

    print("\n\nSample user features:")
    print(features.head(3).T)
