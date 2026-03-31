import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    # Subscription info
    subscription_tier = db.Column(db.String(20), default='FREE') # FREE, STARTER, PRO, ELITE
    subscription_status = db.Column(db.String(20), default='active') # active, expired, trialing
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    razorpay_customer_id = db.Column(db.String(100), nullable=True)
    razorpay_subscription_id = db.Column(db.String(100), nullable=True)
    
    # Usage tracking
    alerts_created = db.Column(db.Integer, default=0)
    indicators_active = db.Column(db.Integer, default=0)
    watchlists_count = db.Column(db.Integer, default=0)

    def is_trial(self):
        return self.subscription_status == 'trialing'

    def get_tier_limits(self):
        limits = {
            'FREE': {
                'max_alerts': 10,
                'max_indicators': 2,
                'max_watchlists': 1,
                'alert_delay': '5-10s',
                'features': ['basic_alerts']
            },
            'STARTER': {
                'max_alerts': 50,
                'max_indicators': 5,
                'max_watchlists': 3,
                'alert_delay': 'real-time',
                'features': ['multi_condition_basic', 'telegram', 'email']
            },
            'PRO': {
                'max_alerts': 200,
                'max_indicators': float('inf'),
                'max_watchlists': float('inf'),
                'alert_delay': 'priority',
                'features': ['advanced_multi_condition', 'basic_backtesting', 'strategy_templates']
            },
            'ELITE': {
                'max_alerts': float('inf'),
                'max_indicators': float('inf'),
                'max_watchlists': float('inf'),
                'alert_delay': 'fastest',
                'features': ['ai_strategy', 'full_backtesting', 'smart_alerts', 'premium_support']
            }
        }
        return limits.get(self.subscription_tier, limits['FREE'])
