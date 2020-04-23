from eth_typing import Hash32
from eth_utils import big_endian_to_int, int_to_big_endian
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, LargeBinary, BigInteger, Integer, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship

from cthaeh.constants import GENESIS_PARENT_HASH

Base = declarative_base()


class BlockUncle(Base):
    __tablename__ = 'blockuncle'

    block_hash = Column(LargeBinary(32), ForeignKey('block.hash'), primary_key=True)
    uncle_hash = Column(LargeBinary(32), ForeignKey('header.hash'), primary_key=True)

    idx = Column(Integer)


class Header(Base):
    __tablename__ = 'header'

    hash = Column(LargeBinary(32), primary_key=True)

    block = relationship("Block", uselist=False, back_populates="header")
    uncle_blocks = relationship(
        "Block",
        secondary="blockuncle",
        order_by=BlockUncle.idx,
    )

    is_canonical = Column(Boolean)

    _parent_hash = Column(LargeBinary(32), ForeignKey('header.hash'), nullable=True)
    uncles_hash = Column(LargeBinary(32))
    coinbase = Column(LargeBinary(20))
    state_root = Column(LargeBinary(32))
    transaction_root = Column(LargeBinary(32))
    receipt_root = Column(LargeBinary(32))
    _bloom = Column(LargeBinary(1024))
    difficulty = Column(BigInteger)
    block_number = Column(BigInteger)
    gas_limit = Column(BigInteger)
    gas_used = Column(BigInteger)
    timestamp = Column(Integer)
    extra_data = Column(LargeBinary)
    mix_hash = Column(LargeBinary(32))
    nonce = Column(LargeBinary(8))

    children = relationship("Header")

    @property
    def parent_hash(self) -> Hash32:
        if self._parent_hash is None:
            return GENESIS_PARENT_HASH
        else:
            return self._parent_hash

    @parent_hash.setter
    def parent_hash(self, value: Hash32) -> None:
        if value == GENESIS_PARENT_HASH:
            self._parent_hash = None
        else:
            self._parent_hash = value


class BlockTransaction(Base):
    __tablename__ = 'blocktransaction'

    block_hash = Column(LargeBinary(32), ForeignKey('block.hash'), primary_key=True)
    transaction_hash = Column(LargeBinary(32), ForeignKey('transaction.hash'), primary_key=True)
    idx = Column(Integer)


class Block(Base):
    __tablename__ = 'block'

    hash = Column(LargeBinary(32), ForeignKey('header.hash'), primary_key=True)
    header = relationship("Header", back_populates="block")

    uncles = relationship(
        "Header",
        secondary="blockuncle",
        order_by=BlockUncle.idx,
    )
    transactions = relationship(
        "Transaction",
        secondary="blocktransaction",
        order_by=BlockTransaction.idx,
    )


class Transaction(Base):
    __tablename__ = 'transaction'

    hash = Column(LargeBinary(32), primary_key=True)

    block_hash = Column(LargeBinary(32), ForeignKey("block.hash"), nullable=True)
    block = relationship("Block")

    blocks = relationship(
        "Block",
        secondary="blocktransaction",
        order_by=BlockTransaction.idx,
    )
    receipt = relationship('Receipt', uselist=False, back_populates="transaction")

    nonce = Column(BigInteger)
    gas_price = Column(BigInteger)
    gas = Column(BigInteger)
    to = Column(LargeBinary(20))
    value = Column(BigInteger)
    data = Column(LargeBinary)
    v = Column(LargeBinary(32))
    r = Column(LargeBinary(32))
    s = Column(LargeBinary(32))


receipt_m2m_topic_table = Table(
    'receipttopics',
    Base.metadata,
    Column('receipt_transaction_hash', LargeBinary(32), ForeignKey('receipt.transaction_hash')),
    Column('log_id', Integer, ForeignKey('log.id'))
)


class Receipt(Base):
    __tablename__ = 'receipt'

    transaction_hash = Column(LargeBinary(32), ForeignKey("transaction.hash"), primary_key=True)
    transaction = relationship('Transaction', back_populates="receipt")

    state_root = Column(LargeBinary(32))
    gas_used = Column(BigInteger)
    _bloom = Column(LargeBinary(1024))
    logs = relationship("Log", back_populates="receipt")

    @property
    def bloom(self) -> int:
        return big_endian_to_int(self._bloom)

    @bloom.setter
    def bloom(self, value: int) -> None:
        self._bloom = int_to_big_endian(value)


class LogTopic(Base):
    __tablename__ = 'logtopic'
    topic_topic = Column(LargeBinary(32), ForeignKey('topic.topic'), primary_key=True)
    log_id = Column(Integer, ForeignKey('log.id'), primary_key=True)

    idx = Column(Integer)

    topic = relationship('Topic')
    log = relationship('Log')


class Log(Base):
    __tablename__ = 'log'

    id = Column(Integer, primary_key=True)

    receipt_hash = Column(LargeBinary(32), ForeignKey('receipt.transaction_hash'))
    receipt = relationship("Receipt", back_populates="logs")

    address = Column(LargeBinary(20))
    topics = relationship(
        "Topic",
        secondary="logtopic",
        order_by=LogTopic.idx,
    )
    data = Column(LargeBinary)


class Topic(Base):
    __tablename__ = 'topic'

    topic = Column(LargeBinary(32), primary_key=True)

    logs = relationship(
        "Log",
        secondary="logtopic",
        order_by=LogTopic.idx,
    )
