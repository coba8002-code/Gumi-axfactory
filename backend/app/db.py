import os


def connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row,
                           connect_timeout=5, options="-c statement_timeout=10000")
