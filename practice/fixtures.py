"""Small, original retail datasets. Seeded variants exercise business edge cases."""
import random

SCHEMA = {
    'customers': [('customer_id', 'INTEGER'), ('name', 'VARCHAR'), ('region', 'VARCHAR'), ('signup_date', 'DATE')],
    'orders': [('order_id', 'INTEGER'), ('customer_id', 'INTEGER'), ('order_date', 'DATE'), ('status', 'VARCHAR'), ('amount', 'DECIMAL(12,2)')],
    'payments': [('event_id', 'INTEGER'), ('payment_id', 'VARCHAR'), ('order_id', 'INTEGER'), ('event_time', 'TIMESTAMP'), ('status', 'VARCHAR'), ('amount', 'DECIMAL(12,2)')],
    'customer_updates': [('update_id', 'INTEGER'), ('customer_id', 'INTEGER'), ('region', 'VARCHAR'), ('effective_at', 'TIMESTAMP'), ('ingested_at', 'TIMESTAMP')],
}

def dataset(seed=0):
    rng = random.Random(seed)
    names = ['Aisha', 'Rohan', 'Meera', 'Kabir', 'Sara', 'Arjun', 'Diya', 'Omar', 'Neha', 'Vikram']
    signup_dates = ['2025-01-01', '2025-01-10', '2025-02-01', '2025-02-20', '2025-03-01', '2025-02-20', '2025-03-01', '2025-01-20', '2025-02-20', '2025-03-01']
    customers = [(i + 1, name, ['North', 'South', 'West', None][i % 4], signup_dates[i]) for i, name in enumerate(names)]
    orders = [
        (1, 1, '2025-01-05', 'completed', 120), (2, 1, '2025-02-12', 'completed', 80),
        (3, 1, '2025-02-12', 'completed', 80), (4, 2, '2025-01-15', 'cancelled', 200),
        (5, 2, '2025-02-18', 'completed', 90), (6, 3, '2025-02-03', 'completed', 150),
        (7, 3, '2025-03-07', 'refunded', 50), (8, 4, '2025-02-23', 'completed', 60),
        (9, 5, '2025-03-11', 'completed', 300), (10, 6, '2025-03-02', 'completed', 0),
        (11, 6, '2025-03-19', 'completed', 100), (12, 7, '2025-03-28', 'completed', 220),
        (13, 8, '2025-02-09', 'completed', 70), (14, 8, '2025-03-03', 'completed', 130),
        (15, 1, '2025-03-31', 'pending', 40), (16, 5, '2025-03-31', 'completed', 300),
        (17, None, '2025-02-04', 'completed', 25),
    ]
    if seed:
        orders = [(a, b, c, d, e + rng.randint(0, 7) * 10) for a, b, c, d, e in orders]
        orders.extend([(18, 9, '2025-03-31', 'completed', 100 + seed), (19, 2, '2025-02-28', 'completed', 90 + seed)])
        if seed % 2:
            orders.append((20, 9, '2025-03-31', 'completed', 100 + seed))
    payments = [
        (1, 'pay_a', 1, '2025-01-05 10:00:00', 'succeeded', 120),
        (2, 'pay_a', 1, '2025-01-05 10:00:00', 'succeeded', 120),
        (3, 'pay_b', 2, '2025-02-12 10:00:00', 'pending', 80),
        (4, 'pay_b', 2, '2025-02-12 10:01:00', 'succeeded', 80),
        (5, 'pay_c', 5, '2025-02-18 11:00:00', 'failed', 90),
        (6, 'pay_d', 6, '2025-02-03 12:00:00', 'succeeded', 150),
        (7, 'pay_d', 6, '2025-02-03 12:00:00', 'refunded', 150),
        (8, 'pay_e', 9, '2025-03-11 14:00:00', 'succeeded', 300),
        (9, 'pay_f', 999, '2025-03-11 15:00:00', 'succeeded', 10),
    ]
    if seed:
        payments.extend([(10, 'pay_g', 18, '2025-03-31 10:00:00', 'succeeded', 100 + seed), (11, 'pay_g', 18, '2025-03-31 10:00:00', 'succeeded', 100 + seed)])
    updates = [
        (1, 1, 'North', '2025-01-01 00:00:00', '2025-01-01 01:00:00'),
        (2, 1, 'South', '2025-02-01 00:00:00', '2025-02-01 01:00:00'),
        (3, 1, 'West', '2025-01-15 00:00:00', '2025-03-01 01:00:00'),
        (4, 2, 'South', '2025-01-01 00:00:00', '2025-01-01 01:00:00'),
        (5, 2, 'North', '2025-03-01 00:00:00', '2025-03-02 01:00:00'),
        (6, 3, 'West', '2025-02-01 00:00:00', '2025-02-01 01:00:00'),
        (7, 3, 'North', '2025-02-01 00:00:00', '2025-02-02 01:00:00'),
    ]
    if seed:
        updates.append((8, 4, 'West', '2025-03-20 00:00:00', '2025-03-21 00:00:00'))
    return dict(customers=customers, orders=orders, payments=payments, customer_updates=updates)

def populate(connection, seed):
    for table, columns in SCHEMA.items():
        connection.execute(f'CREATE TABLE {table} (' + ', '.join(f'{name} {kind}' for name, kind in columns) + ')')
    for table, rows in dataset(seed).items():
        connection.executemany(f'INSERT INTO {table} VALUES (' + ','.join('?' for _ in SCHEMA[table]) + ')', rows)
