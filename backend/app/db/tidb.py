import os
from sqlalchemy import create_engine, text

ENGINE = create_engine(os.environ["TIDB_URL"], pool_pre_ping=True)
