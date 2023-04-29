from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from flask_login import UserMixin
import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(Enum("buyer", "seller", "admin"), nullable=False)

    auctions = relationship("Auction", backref="user")
    bids = relationship("Bid", backref="user")

class Auction(db.Model):
    id = Column(Integer, primary_key=True)
    image = Column(String(100), nullable=False)
    startPrice = Column(Float, nullable=False)
    reservePrice = Column(Float, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    uploadDate = Column(DateTime, default=datetime.datetime.utcnow)
    expiryDate = Column(DateTime, nullable=False)
    userId = Column(Integer, ForeignKey("user.id"))

    bids = relationship("Bid", backref="auction")

class Bid(db.Model):
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    userId = Column(Integer, ForeignKey("user.id"))
    auctionId = Column(Integer, ForeignKey("auction.id"))
    result = Column(Enum("winning", "losing", "pending"), nullable=False)