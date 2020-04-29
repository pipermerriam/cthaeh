import pytest
from sqlalchemy.exc import IntegrityError

from cthaeh.constants import GENESIS_PARENT_HASH
from cthaeh.models import Block, Header, Log, Receipt, Topic, Transaction
from cthaeh.tools.factories import (
    BlockFactory,
    BlockTransactionFactory,
    BlockUncleFactory,
    Hash32Factory,
    HeaderFactory,
    LogFactory,
    LogTopicFactory,
    ReceiptFactory,
    TopicFactory,
    TransactionFactory,
)


def test_orm_single_topic(session):
    topic = TopicFactory()

    with session.begin_nested():
        session.add(topic)

    topic_from_db = session.query(Topic).filter(Topic.topic == topic.topic).one()

    assert topic_from_db.topic == topic.topic


def test_orm_log_without_topics(session):
    log = LogFactory()

    with session.begin_nested():
        session.add(log)

    log_from_db = session.query(Log).filter(Log.id == log.id).one()

    assert log_from_db.id == log.id


def test_orm_log_with_single_topic(session):
    topic = TopicFactory()
    log = LogFactory()
    log_topic = LogTopicFactory(log=log, topic=topic, idx=0)

    with session.begin_nested():
        session.add_all((log, topic, log_topic))

    log_from_db = session.query(Log).filter(Log.id == log.id).one()

    assert log_from_db.id == log.id
    assert len(log_from_db.topics) == 1


def test_orm_log_with_multiple_topics(session):
    topic_a, topic_b, topic_c = TopicFactory.create_batch(3)
    log = LogFactory()
    log_topic_0 = LogTopicFactory(topic=topic_b, log=log, idx=0)
    log_topic_1 = LogTopicFactory(topic=topic_a, log=log, idx=1)
    log_topic_2 = LogTopicFactory(topic=topic_c, log=log, idx=2)

    with session.begin_nested():
        session.add_all(
            (log, topic_a, topic_b, topic_c, log_topic_0, log_topic_1, log_topic_2)
        )

    log_from_db = session.query(Log).filter(Log.id == log.id).one()

    assert log_from_db.id == log.id
    assert len(log_from_db.topics) == 3
    assert log.topics[0].topic == topic_b.topic
    assert log.topics[1].topic == topic_a.topic
    assert log.topics[2].topic == topic_c.topic


def test_orm_receipt_without_logs(session):
    receipt = ReceiptFactory()

    with session.begin_nested():
        session.add(receipt)

    receipt_from_db = (
        session.query(Receipt)
        .filter(Receipt.transaction_hash == receipt.transaction_hash)
        .one()
    )

    assert receipt_from_db.transaction_hash == receipt.transaction_hash
    assert len(receipt.logs) == 0
    assert receipt_from_db.transaction.hash == receipt.transaction_hash


def test_orm_receipt_with_single_log(session):
    receipt = ReceiptFactory()
    log = LogFactory(receipt=receipt, idx=0)

    with session.begin_nested():
        session.add_all((log, receipt))

    receipt_from_db = (
        session.query(Receipt)
        .filter(Receipt.transaction_hash == receipt.transaction_hash)
        .one()
    )

    assert receipt_from_db.transaction_hash == receipt.transaction_hash
    assert len(receipt.logs) == 1
    assert receipt.logs[0].id == log.id


def test_orm_receipt_with_multiple_logs(session):
    receipt = ReceiptFactory()
    log_b = LogFactory(receipt=receipt, idx=1)
    log_a = LogFactory(receipt=receipt, idx=0)
    log_c = LogFactory(receipt=receipt, idx=2)

    with session.begin_nested():
        session.add_all((log_b, log_a, log_c, receipt))

    receipt_from_db = (
        session.query(Receipt)
        .filter(Receipt.transaction_hash == receipt.transaction_hash)
        .one()
    )

    assert receipt_from_db.transaction_hash == receipt.transaction_hash
    assert len(receipt_from_db.logs) == 3
    # TODO: the ordering across the many-to-many relationship isn't working the
    # way it is supposed to.
    # assert receipt_from_db.logs[0].id == log_a.id
    # assert receipt_from_db.logs[1].id == log_b.id
    # assert receipt_from_db.logs[2].id == log_c.id


def test_orm_simple_transaction(session):
    transaction = TransactionFactory()

    with session.begin_nested():
        session.add(transaction)

    transaction_from_db = (
        session.query(Transaction).filter(Transaction.hash == transaction.hash).one()
    )
    assert transaction_from_db.hash == transaction.hash


def test_orm_transaction_without_block(session):
    transaction = TransactionFactory(block=None)

    with session.begin_nested():
        session.add(transaction)

    transaction_from_db = (
        session.query(Transaction).filter(Transaction.hash == transaction.hash).one()
    )
    assert transaction_from_db.hash == transaction.hash
    assert transaction.block is None
    assert len(transaction.blocks) == 0


def test_orm_transaction_with_non_canonical_block(session):
    block = BlockFactory(header__is_canonical=False)
    transaction = TransactionFactory(block=None)
    block_transaction = BlockTransactionFactory(
        block=block, transaction=transaction, idx=0
    )

    with session.begin_nested():
        session.add_all((block, transaction, block_transaction))

    transaction_from_db = (
        session.query(Transaction).filter(Transaction.hash == transaction.hash).one()
    )
    assert transaction_from_db.hash == transaction.hash
    assert transaction.block is None
    assert len(transaction.blocks) == 1
    assert transaction.blocks[0].header_hash == block.header_hash


def test_orm_simple_block(session):
    block = BlockFactory()

    with session.begin_nested():
        session.add(block)

    block_from_db = (
        session.query(Block).filter(Block.header_hash == block.header_hash).one()
    )

    assert block_from_db.header_hash == block.header_hash
    assert len(block.transactions) == 0


def test_orm_block_transaction_ordering(session):
    block = BlockFactory()

    transaction_b = TransactionFactory(block=block)
    transaction_a = TransactionFactory(block=block)
    transaction_c = TransactionFactory(block=block)

    block_transaction_b = BlockTransactionFactory(
        block=block, transaction=transaction_b, idx=1
    )
    block_transaction_a = BlockTransactionFactory(
        block=block, transaction=transaction_a, idx=0
    )
    block_transaction_c = BlockTransactionFactory(
        block=block, transaction=transaction_c, idx=2
    )

    with session.begin_nested():
        session.add_all(
            (
                block,
                transaction_a,
                transaction_b,
                transaction_c,
                block_transaction_a,
                block_transaction_b,
                block_transaction_c,
            )
        )

    block_from_db = (
        session.query(Block).filter(Block.header_hash == block.header_hash).one()
    )

    assert len(block_from_db.transactions) == 3
    assert block_from_db.transactions[0].hash == transaction_a.hash
    assert block_from_db.transactions[1].hash == transaction_b.hash
    assert block_from_db.transactions[2].hash == transaction_c.hash


def test_orm_block_with_uncles(session):
    block = BlockFactory()

    uncle_b = HeaderFactory()
    uncle_a = HeaderFactory()
    uncle_c = HeaderFactory()

    block_uncle_b = BlockUncleFactory(block=block, uncle=uncle_b, idx=1)
    block_uncle_a = BlockUncleFactory(block=block, uncle=uncle_a, idx=0)
    block_uncle_c = BlockUncleFactory(block=block, uncle=uncle_c, idx=2)

    with session.begin_nested():
        session.add_all(
            (
                block,
                uncle_a,
                uncle_b,
                uncle_c,
                block_uncle_a,
                block_uncle_b,
                block_uncle_c,
            )
        )

    block_from_db = (
        session.query(Block).filter(Block.header_hash == block.header_hash).one()
    )

    assert len(block_from_db.uncles) == 3
    assert block_from_db.uncles[0].hash == uncle_a.hash
    assert block_from_db.uncles[1].hash == uncle_b.hash
    assert block_from_db.uncles[2].hash == uncle_c.hash


def test_orm_simple_header(session):
    header = HeaderFactory()

    with session.begin_nested():
        session.add(header)

    header_from_db = session.query(Header).filter(Header.hash == header.hash).one()

    assert header_from_db.hash == header.hash


def test_orm_genesis_header(session):
    header = HeaderFactory(parent_hash=None)

    with session.begin_nested():
        session.add(header)

    header_from_db = session.query(Header).filter(Header.hash == header.hash).one()

    assert header_from_db.hash == header.hash
    assert header_from_db.parent_hash == GENESIS_PARENT_HASH


def test_orm_detatched_header(session):
    parent_hash = Hash32Factory()
    header = HeaderFactory(parent_hash=None, detatched_parent_hash=parent_hash)

    with session.begin_nested():
        session.add(header)

    header_from_db = session.query(Header).filter(Header.hash == header.hash).one()

    assert header_from_db.hash == header.hash
    assert header_from_db.parent_hash == parent_hash


def test_orm_header_invalid_with_multiple_parent_hashes(session):
    parent_hash_a = Hash32Factory()
    parent_hash_b = Hash32Factory()
    header = HeaderFactory(parent_hash=parent_hash_a, detatched_parent_hash=parent_hash_b)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(header)
