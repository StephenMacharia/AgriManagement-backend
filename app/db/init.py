from app.models.user import User
from app.models.product import Product
from app.models.produce import Produce
from app.models.credit import CreditAccount, CreditRepayment
from app.models.transaction import Transaction, TransactionItem, Commission
from app.db.session import engine, Base

def init_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)