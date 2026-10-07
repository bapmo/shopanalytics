import sqlite3, os

if os.path.exists("shop.db"):
    os.remove("shop.db")
conn = sqlite3.connect("shop.db")

conn.executescript("""
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT,
    signup_date TEXT
);
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    price REAL
);
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    order_date TEXT
);
CREATE TABLE order_items (
    order_id INTEGER REFERENCES orders(order_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER,
    PRIMARY KEY (order_id, product_id)
);

INSERT INTO customers VALUES
 (1,'Alice','North','2025-01-10'),(2,'Bob','South','2025-02-14'),
 (3,'Chen','East','2025-03-02'),(4,'Dana','North','2025-03-20'),
 (5,'Eli','West','2025-04-05');

INSERT INTO products VALUES
 (1,'Laptop','Electronics',900),(2,'Headphones','Electronics',120),
 (3,'Desk','Furniture',250),(4,'Chair','Furniture',180),
 (5,'Notebook','Stationery',5);

INSERT INTO orders VALUES
 (1,1,'2025-05-01'),(2,2,'2025-05-03'),(3,1,'2025-06-11'),
 (4,3,'2025-06-15'),(5,4,'2025-07-02'),(6,2,'2025-07-19');

INSERT INTO order_items VALUES
 (1,1,1),(1,2,1),(2,3,1),(3,5,10),(4,4,2),(5,1,1),(5,3,1),(6,2,2);
""")
conn.commit()
conn.close()
print("shop.db created")