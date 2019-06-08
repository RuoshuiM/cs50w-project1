import psycopg2
from sqlalchemy import create_engine
import csv

# local test database 
# engine = create_engine('postgresql://postgres:postgres@localhost:5432/project1')

# actual database
engine = create_engine("postgres://jgiduehaaiifrf:c8f46939b0036d5279517bd6e058b003814d303246b41a14eab3b0a066331453@ec2-50-19-127-115.compute-1.amazonaws.com:5432/d4jthl04loj6n1")

db = engine.connect()

fin = open("books.csv")
reader = csv.reader(fin)

db.execute("""CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    isbn VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    year INTEGER NOT NULL
    );""")

next(reader)  # get rid of title line

for info in reader:
    db.execute("""INSERT INTO books 
                    (isbn, title, author, year)
                    VALUES (%s, %s, %s, %s)""", info)


