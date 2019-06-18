from os import getenv
import psycopg2
from sqlalchemy import create_engine
from sys import argv

# local test database 
engine = create_engine('postgresql://postgres:postgres@localhost:5432/project1')

# if not getenv("DATABASE_URL"):
#     raise RuntimeError("DATABASE_URL is not set")

# # actual database
# engine = create_engine(getenv("DATABASE_URL"))

db = engine.connect()

def create():    
    # table of users
    db.execute("""CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username TEXT NOT NULL,
        passhash TEXT NOT NULL
        )""")

    db.execute("""CREATE TABLE reviews (
        user_id INTEGER REFERENCES users(id),
        book_id INTEGER REFERENCES books(id),
        rating INTEGER NOT NULL,
        text TEXT NOT NULL,
        PRIMARY KEY (user_id, book_id)
    )""")

def get(sql):
    result = db.execute(sql)
    return result.fetchall()
    
def do(sql):
    db.execute(sql)

# def drop(table):
#     db.execute("DROP TABLE users")

if __name__ == "__main__":
    if len(argv) <= 1:
        print("Usage: get/create")
        exit(1)
    if argv[1] == "get":
        print(get(argv[2]))
    elif argv[1] == "create":
        create()
    elif argv[1] == "do":
        do(argv[2])
    # elif argv[1] == "drop":
    #     drop(argv[2])
    else:
        print(argv)

