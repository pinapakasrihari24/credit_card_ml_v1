"""
Credit Card Fraud Detection - Flask Application
Supports both CSV files (local) and PostgreSQL (GCP Cloud SQL)
"""

import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, current_user, UserMixin

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')
app.config['DATA_PATH'] = os.environ.get('DATA_PATH', '/app/data')

USE_DATABASE = bool(app.config['DATABASE_URL'])

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    """Admin user for authentication."""

    def __init__(self, username):
        self.id = username


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User(user_id)


# Cache for data
_data_cache = {}


def get_db_connection():
    """Get database connection for Cloud SQL."""
    import psycopg2
    return psycopg2.connect(app.config['DATABASE_URL'])


def to_scalar(val, default=None):
    """Convert pandas scalar to Python scalar."""
    if val is None:
        return default
    if isinstance(val, (pd.Series, pd.DataFrame)):
        return default
    return val


def df_to_records(df):
    """Convert DataFrame to list of dicts with scalar values."""
    if df.empty:
        return []
    records = df.to_dict('records')
    result = []
    for record in records:
        clean_record = {}
        for k, v in record.items():
            if isinstance(v, (pd.Timestamp, pd.Timedelta)):
                clean_record[k] = str(v)
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                clean_record[k] = float(v) if isinstance(v, float) else int(v)
            elif isinstance(v, bool):
                clean_record[k] = bool(v)
            else:
                clean_record[k] = v
        result.append(clean_record)
    return result


def load_data():
    """Load and cache datasets."""
    if not _data_cache:
        if USE_DATABASE:
            # Load from Cloud SQL
            conn = get_db_connection()
            _data_cache['profiles'] = pd.read_sql('SELECT * FROM user_profiles', conn)
            _data_cache['transactions'] = pd.read_sql('SELECT * FROM transactions', conn)
            _data_cache['features'] = pd.read_sql('SELECT * FROM user_features', conn)
            conn.close()
        else:
            # Load from CSV files
            data_path = app.config['DATA_PATH']
            profiles_path = os.path.join(data_path, 'sample', 'sample_credit_card_profiles.csv')
            tx_path = os.path.join(data_path, 'sample', 'sample_credit_card_transactions.csv')
            features_path = os.path.join(data_path, 'sample', 'sample_credit_card_user_features.csv')

            if not os.path.exists(profiles_path):
                profiles_path = os.path.join(data_path, 'raw', 'credit_card_profiles.csv')
                tx_path = os.path.join(data_path, 'raw', 'credit_card_transactions.csv')
                features_path = os.path.join(data_path, 'raw', 'credit_card_user_features.csv')

            _data_cache['profiles'] = pd.read_csv(profiles_path)
            _data_cache['transactions'] = pd.read_csv(tx_path, parse_dates=['timestamp'])
            _data_cache['features'] = pd.read_csv(features_path)

    return _data_cache


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    from flask import flash
    from auth import verify_admin_password, get_admin_username

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if verify_admin_password(username, password):
            from flask_login import login_user
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Admin logout."""
    from flask_login import logout_user
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Home page with search form."""
    data = load_data()
    total_users = int(len(data['profiles']))
    total_transactions = int(len(data['transactions']))
    fraud_count = int(data['transactions']['is_fraudulent'].sum())
    fraud_rate = round((fraud_count / total_transactions * 100), 2) if total_transactions > 0 else 0

    stats = {
        'total_users': total_users,
        'total_transactions': total_transactions,
        'fraud_count': fraud_count,
        'fraud_rate': fraud_rate
    }
    return render_template('index.html', stats=stats)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Search for a user by ID."""
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
    else:
        user_id = request.args.get('user_id', '').strip()

    if not user_id:
        return redirect(url_for('index'))

    data = load_data()

    # Find user in profiles
    profile_mask = data['profiles']['user_id'] == user_id
    if not profile_mask.any():
        return render_template('user_not_found.html', user_id=user_id)

    user_profile = data['profiles'][profile_mask].iloc[0]

    # Get user transactions
    tx_mask = data['transactions']['user_id'] == user_id
    user_tx = data['transactions'][tx_mask].sort_values('timestamp', ascending=False)

    # Get user features
    feat_mask = data['features']['user_id'] == user_id
    user_features = data['features'][feat_mask].iloc[0] if feat_mask.any() else None

    # Fraud transactions
    fraud_mask = tx_mask & (data['transactions']['is_fraudulent'] == True)
    fraudulent_tx = data['transactions'][fraud_mask]

    # Spending by category
    if len(user_tx) > 0:
        spending_grouped = user_tx.groupby('merchant_category')['amount'].agg(['sum', 'count', 'mean'])
        spending_by_category = {
            cat: {
                'Total': round(float(row['sum']), 2),
                'Count': int(row['count']),
                'Average': round(float(row['mean']), 2)
            }
            for cat, row in spending_grouped.iterrows()
        }
    else:
        spending_by_category = {}

    # Time analysis
    if len(user_tx) > 0:
        tx_by_hour = user_tx.groupby('hour_of_day')['amount'].count().to_dict()
        tx_by_day = user_tx.groupby('is_weekend')['amount'].count().to_dict()
        weekend_count = int(tx_by_day.get(True, 0))
        weekday_count = int(tx_by_day.get(False, 0))
    else:
        tx_by_hour = {}
        weekend_count = 0
        weekday_count = 0

    # Profile as dict with scalar values
    profile_dict = {
        'user_id': str(user_profile['user_id']),
        'credit_score': int(user_profile['credit_score']),
        'age': int(user_profile['age']),
        'annual_income': float(user_profile['annual_income']),
        'credit_limit': float(user_profile['credit_limit']),
        'risk_profile': str(user_profile['risk_profile']),
        'account_age_days': int(user_profile['account_age_days']),
    }

    # Features as dict with scalar values
    features_dict = None
    if user_features is not None:
        features_dict = {
            'utilization': round(float(user_features['utilization']), 4),
            'income_to_limit': round(float(user_features['income_to_limit']), 4),
        }

    user_data = {
        'profile': profile_dict,
        'features': features_dict,
        'total_transactions': int(len(user_tx)),
        'fraudulent_transactions': int(len(fraudulent_tx)),
        'fraud_amount': round(float(fraudulent_tx['amount'].sum()), 2) if len(fraudulent_tx) > 0 else 0,
        'fraudulent_tx': df_to_records(fraudulent_tx.head(10)),
        'recent_transactions': df_to_records(user_tx.head(20)),
        'spending_by_category': spending_by_category,
        'total_spent': round(float(user_tx['amount'].sum()), 2) if len(user_tx) > 0 else 0,
        'avg_transaction': round(float(user_tx['amount'].mean()), 2) if len(user_tx) > 0 else 0,
        'max_transaction': round(float(user_tx['amount'].max()), 2) if len(user_tx) > 0 else 0,
        'weekend_count': weekend_count,
        'weekday_count': weekday_count,
        'tx_by_hour': {int(k): int(v) for k, v in tx_by_hour.items()},
        'risk_profile': str(user_profile['risk_profile']),
    }

    return render_template('user_detail.html', user_data=user_data, user_id=user_id)


@app.route('/api/user/<user_id>')
@login_required
def api_user(user_id):
    """API endpoint for user data."""
    data = load_data()

    profile_mask = data['profiles']['user_id'] == user_id
    if not profile_mask.any():
        return jsonify({'error': 'User not found'}), 404

    user_profile = data['profiles'][profile_mask].iloc[0]
    tx_mask = data['transactions']['user_id'] == user_id
    user_tx = data['transactions'][tx_mask]
    feat_mask = data['features']['user_id'] == user_id
    user_features = data['features'][feat_mask].iloc[0] if feat_mask.any() else None

    return jsonify({
        'profile': {
            'user_id': str(user_profile['user_id']),
            'credit_score': int(user_profile['credit_score']),
            'age': int(user_profile['age']),
            'annual_income': float(user_profile['annual_income']),
            'credit_limit': float(user_profile['credit_limit']),
            'risk_profile': str(user_profile['risk_profile']),
        },
        'transactions': df_to_records(user_tx),
        'features': {k: float(v) for k, v in user_features.to_dict().items()
                     if k != 'user_id' and pd.api.types.is_numeric_dtype(user_features[k])} if user_features is not None else {},
        'fraud_count': int(user_tx['is_fraudulent'].sum()),
        'total_spent': float(user_tx['amount'].sum()),
    })


@app.route('/fraud_list')
@login_required
def fraud_list():
    """List all users with fraudulent transactions."""
    data = load_data()

    fraud_mask = data['transactions']['is_fraudulent'] == True
    fraud_user_ids = data['transactions'][fraud_mask]['user_id'].unique()

    fraud_summary = []
    for uid in fraud_user_ids[:50]:
        tx_mask = data['transactions']['user_id'] == uid
        user_tx = data['transactions'][tx_mask]
        fraud_tx = user_tx[user_tx['is_fraudulent'] == True]
        profile_mask = data['profiles']['user_id'] == uid

        fraud_summary.append({
            'user_id': str(uid),
            'total_tx': int(len(user_tx)),
            'fraud_count': int(len(fraud_tx)),
            'fraud_amount': round(float(fraud_tx['amount'].sum()), 2),
            'risk_profile': str(data['profiles'][profile_mask].iloc[0]['risk_profile']) if profile_mask.any() else 'unknown'
        })

    return render_template('fraud_list.html', fraud_summary=fraud_summary)


@app.route('/health')
def health():
    """Health check endpoint for Cloud Run."""
    return jsonify({'status': 'healthy', 'database': 'connected' if USE_DATABASE else 'csv'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting Credit Card Fraud Detection UI on port {port}")
    print(f"Database mode: {'Cloud SQL' if USE_DATABASE else 'CSV files'}")
    app.run(host='0.0.0.0', port=port, debug=USE_DATABASE)
