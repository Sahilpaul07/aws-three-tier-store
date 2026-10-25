from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import os
import pymysql
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]


def get_db_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        port=3306,
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/")
def home():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, description, price, stock FROM products ORDER BY id"
            )
            products = cursor.fetchall()
    finally:
        conn.close()

    cart = session.get("cart", {})
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Sahil Store</title>
      <style>
        *{box-sizing:border-box}
        body{margin:0;font-family:Arial;background:#f3f5f9;color:#172033}
        header{background:#14213d;color:white;padding:24px 7%}
        main{max-width:1100px;margin:30px auto;padding:0 20px}
        .products{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px}
        .card{background:white;border-radius:12px;padding:22px;box-shadow:0 4px 16px #14213d12}
        .price{font-size:22px;font-weight:bold;margin:14px 0}
        .button{display:inline-block;background:#2563eb;color:white;border:0;padding:10px 15px;border-radius:7px;text-decoration:none;cursor:pointer}
        input{padding:10px;border:1px solid #ccd2dc;border-radius:6px;max-width:100%}
        .panel{background:white;padding:22px;border-radius:12px;margin:25px 0}
        .msg{background:#fff3cd;padding:12px;border-radius:7px;margin:10px 0}
      </style>
    </head>
    <body>
      <header><h1>🛍️ Sahil Store</h1><p>Simple shopping, powered by AWS</p></header>
      <main>
        <h2>Our Products</h2>
        <p>Products are loaded live from Amazon RDS.</p>
        {% for message in get_flashed_messages() %}
          <div class="msg">{{ message }}</div>
        {% endfor %}
        <section class="products">
        {% for p in products %}
          <article class="card">
            <h3>{{ p.name }}</h3>
            <p>{{ p.description or "Quality product" }}</p>
            <div class="price">₹{{ "%.2f"|format(p.price) }}</div>
            <p>In stock: {{ p.stock }}</p>
            {% if p.stock > 0 %}
            <form method="post" action="{{ url_for('add_to_cart', product_id=p.id) }}">
              <label>Quantity
                <input type="number" name="quantity" min="1" max="{{ p.stock }}" value="1" required>
              </label>
              <button class="button" type="submit">Add to Cart</button>
            </form>
            {% else %}<p>Out of stock</p>{% endif %}
          </article>
        {% else %}<p>No products available.</p>{% endfor %}
        </section>

        <section class="panel">
          <h2>Your Cart</h2>
          {% if cart_items %}
            {% for item in cart_items %}
              <p>{{ item.name }} × {{ item.quantity }} — ₹{{ "%.2f"|format(item.subtotal) }}</p>
              <form method="post" action="{{ url_for('update_cart', product_id=item.id) }}">
                <input type="number" name="quantity" min="0" max="{{ item.stock }}" value="{{ item.quantity }}" required>
                <button class="button" type="submit">Update (0 removes)</button>
              </form>
            {% endfor %}
            <h3>Total: ₹{{ "%.2f"|format(total) }}</h3>
            <a class="button" href="{{ url_for('checkout') }}">Proceed to Checkout</a>
          {% else %}<p>Your cart is empty.</p>{% endif %}
        </section>
        <p><a href="/db-test">Check database</a></p>
      </main>
    </body>
    </html>
    """, products=products, cart_items=get_cart_items(), total=get_cart_total(),
       cart=cart)


def get_cart_items(cursor=None):
    cart = session.get("cart", {})
    if not cart:
        return []
    own_conn = cursor is None
    conn = get_db_connection() if own_conn else None
    cur = cursor or conn.cursor()
    try:
        ids = [int(pid) for pid in cart if str(pid).isdigit()]
        if not ids:
            return []
        placeholders = ",".join(["%s"] * len(ids))
        cur.execute(
            f"SELECT id, name, price, stock FROM products WHERE id IN ({placeholders})",
            ids
        )
        products = cur.fetchall()
        result = []
        for p in products:
            qty = int(cart.get(str(p["id"]), 0))
            if qty > 0:
                result.append({
                    "id": p["id"], "name": p["name"], "price": p["price"],
                    "stock": p["stock"], "quantity": qty,
                    "subtotal": Decimal(str(p["price"])) * qty
                })
        return result
    finally:
        if own_conn:
            conn.close()


def get_cart_total():
    return sum(
        (item["subtotal"] for item in get_cart_items()),
        Decimal("0.00")
    )


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    try:
        quantity = int(request.form.get("quantity", "1"))
        if quantity < 1:
            raise ValueError
    except ValueError:
        flash("Please enter a valid quantity.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT stock FROM products WHERE id=%s", (product_id,))
            product = cursor.fetchone()
        if not product:
            flash("Product not found.")
            return redirect(url_for("home"))
        current = int(session.get("cart", {}).get(str(product_id), 0))
        if current + quantity > int(product["stock"]):
            flash("Requested quantity exceeds available stock.")
            return redirect(url_for("home"))
        cart = session.get("cart", {})
        cart[str(product_id)] = current + quantity
        session["cart"] = cart
        flash("Product added to cart.")
    finally:
        conn.close()
    return redirect(url_for("home"))


@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    try:
        quantity = int(request.form.get("quantity", "0"))
        if quantity < 0:
            raise ValueError
    except ValueError:
        flash("Invalid quantity.")
        return redirect(url_for("home"))

    cart = session.get("cart", {})
    if quantity == 0:
        cart.pop(str(product_id), None)
    else:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT stock FROM products WHERE id=%s", (product_id,))
                product = cursor.fetchone()
            if not product or quantity > int(product["stock"]):
                flash("Quantity exceeds available stock.")
                return redirect(url_for("home"))
        finally:
            conn.close()
        cart[str(product_id)] = quantity
    session["cart"] = cart
    return redirect(url_for("home"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = get_cart_items()
    if not items:
        flash("Your cart is empty.")
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        email = request.form.get("customer_email", "").strip()
        if not name or len(name) > 150 or "@" not in email or len(email) > 255:
            flash("Enter a valid name and email address.")
            return redirect(url_for("checkout"))

        conn = get_db_connection()
        try:
            conn.begin()
            with conn.cursor() as cursor:
                cart = session.get("cart", {})
                product_ids = sorted(int(pid) for pid in cart)
                total = Decimal("0.00")
                locked = {}

                for pid in product_ids:
                    cursor.execute(
                        "SELECT id, name, price, stock FROM products WHERE id=%s FOR UPDATE",
                        (pid,)
                    )
                    product = cursor.fetchone()
                    qty = int(cart[str(pid)])
                    if not product or qty < 1 or qty > int(product["stock"]):
                        conn.rollback()
                        flash("Stock changed. Please review your cart.")
                        return redirect(url_for("home"))
                    locked[pid] = (product, qty)
                    total += Decimal(str(product["price"])) * qty

                cursor.execute(
                    "INSERT INTO orders (customer_name, customer_email, total_amount, status) "
                    "VALUES (%s, %s, %s, %s)",
                    (name, email, total, "Placed")
                )
                order_id = cursor.lastrowid

                for pid, (product, qty) in locked.items():
                    cursor.execute(
                        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                        "VALUES (%s, %s, %s, %s)",
                        (order_id, pid, qty, product["price"])
                    )
                    cursor.execute(
                        "UPDATE products SET stock = stock - %s WHERE id = %s AND stock >= %s",
                        (qty, pid, qty)
                    )
                    if cursor.rowcount != 1:
                        raise RuntimeError("Stock update failed")

            conn.commit()
            session["cart"] = {}
            return render_template_string("""
              <html><head><title>Order placed</title></head>
              <body style="font-family:Arial;background:#f3f5f9;padding:40px">
                <h1>Order placed successfully!</h1>
                <p>Order ID: {{ order_id }}</p>
                <p>Total: ₹{{ "%.2f"|format(total) }}</p>
                <a href="/">Back to Sahil Store</a>
              </body></html>
            """, order_id=order_id, total=total)
        except Exception:
            conn.rollback()
            app.logger.exception("Order placement failed")
            flash("Unable to place order. Please check application logs.")
            return redirect(url_for("checkout"))
        finally:
            conn.close()

    return render_template_string("""
      <!doctype html><html><head><meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Checkout - Sahil Store</title>
      <style>body{font-family:Arial;background:#f3f5f9;padding:30px}
      .panel{max-width:600px;margin:auto;background:white;padding:25px;border-radius:12px}
      input{display:block;width:100%;padding:12px;margin:8px 0 18px}
      button{background:#2563eb;color:white;border:0;padding:12px;border-radius:7px}
      </style></head><body><div class="panel">
      <h1>Checkout</h1>
      {% for message in get_flashed_messages() %}<p>{{ message }}</p>{% endfor %}
      {% for item in items %}<p>{{ item.name }} × {{ item.quantity }} — ₹{{ "%.2f"|format(item.subtotal) }}</p>{% endfor %}
      <h3>Total: ₹{{ "%.2f"|format(total) }}</h3>
      <form method="post">
        <label>Customer name</label><input name="customer_name" maxlength="150" required>
        <label>Email</label><input name="customer_email" type="email" maxlength="255" required>
        <button type="submit">Place Order</button>
      </form><p><a href="/">Back to store</a></p>
      </div></body></html>
    """, items=items, total=sum((i["subtotal"] for i in items), Decimal("0.00")))


@app.route("/db-test")
def db_test():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS db_name")
            db_name = cursor.fetchone()["db_name"]
        return f"<h1>Database Connected Successfully!</h1><p>Database: {db_name}</p><p><a href='/'>Back to Store</a></p>"
    except Exception:
        app.logger.exception("Database connection failed")
        return "Database connection failed. Check application logs.", 500
    finally:
        conn.close()


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
[ec2-user@ip-10-0-11-17 app]$ cat /home/ec2-user/app/app.py
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import os
import pymysql
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]


def get_db_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        port=3306,
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/")
def home():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, description, price, stock FROM products ORDER BY id"
            )
            products = cursor.fetchall()
    finally:
        conn.close()

    cart = session.get("cart", {})
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Sahil Store</title>
      <style>
        *{box-sizing:border-box}
        body{margin:0;font-family:Arial;background:#f3f5f9;color:#172033}
        header{background:#14213d;color:white;padding:24px 7%}
        main{max-width:1100px;margin:30px auto;padding:0 20px}
        .products{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px}
        .card{background:white;border-radius:12px;padding:22px;box-shadow:0 4px 16px #14213d12}
        .price{font-size:22px;font-weight:bold;margin:14px 0}
        .button{display:inline-block;background:#2563eb;color:white;border:0;padding:10px 15px;border-radius:7px;text-decoration:none;cursor:pointer}
        input{padding:10px;border:1px solid #ccd2dc;border-radius:6px;max-width:100%}
        .panel{background:white;padding:22px;border-radius:12px;margin:25px 0}
        .msg{background:#fff3cd;padding:12px;border-radius:7px;margin:10px 0}
      </style>
    </head>
    <body>
      <header><h1>🛍️ Sahil Store</h1><p>Simple shopping, powered by AWS</p></header>
      <main>
        <h2>Our Products</h2>
        <p>Products are loaded live from Amazon RDS.</p>
        {% for message in get_flashed_messages() %}
          <div class="msg">{{ message }}</div>
        {% endfor %}
        <section class="products">
        {% for p in products %}
          <article class="card">
            <h3>{{ p.name }}</h3>
            <p>{{ p.description or "Quality product" }}</p>
            <div class="price">₹{{ "%.2f"|format(p.price) }}</div>
            <p>In stock: {{ p.stock }}</p>
            {% if p.stock > 0 %}
            <form method="post" action="{{ url_for('add_to_cart', product_id=p.id) }}">
              <label>Quantity
                <input type="number" name="quantity" min="1" max="{{ p.stock }}" value="1" required>
              </label>
              <button class="button" type="submit">Add to Cart</button>
            </form>
            {% else %}<p>Out of stock</p>{% endif %}
          </article>
        {% else %}<p>No products available.</p>{% endfor %}
        </section>

        <section class="panel">
          <h2>Your Cart</h2>
          {% if cart_items %}
            {% for item in cart_items %}
              <p>{{ item.name }} × {{ item.quantity }} — ₹{{ "%.2f"|format(item.subtotal) }}</p>
              <form method="post" action="{{ url_for('update_cart', product_id=item.id) }}">
                <input type="number" name="quantity" min="0" max="{{ item.stock }}" value="{{ item.quantity }}" required>
                <button class="button" type="submit">Update (0 removes)</button>
              </form>
            {% endfor %}
            <h3>Total: ₹{{ "%.2f"|format(total) }}</h3>
            <a class="button" href="{{ url_for('checkout') }}">Proceed to Checkout</a>
          {% else %}<p>Your cart is empty.</p>{% endif %}
        </section>
        <p><a href="/db-test">Check database</a></p>
      </main>
    </body>
    </html>
    """, products=products, cart_items=get_cart_items(), total=get_cart_total(),
       cart=cart)


def get_cart_items(cursor=None):
    cart = session.get("cart", {})
    if not cart:
        return []
    own_conn = cursor is None
    conn = get_db_connection() if own_conn else None
    cur = cursor or conn.cursor()
    try:
        ids = [int(pid) for pid in cart if str(pid).isdigit()]
        if not ids:
            return []
        placeholders = ",".join(["%s"] * len(ids))
        cur.execute(
            f"SELECT id, name, price, stock FROM products WHERE id IN ({placeholders})",
            ids
        )
        products = cur.fetchall()
        result = []
        for p in products:
            qty = int(cart.get(str(p["id"]), 0))
            if qty > 0:
                result.append({
                    "id": p["id"], "name": p["name"], "price": p["price"],
                    "stock": p["stock"], "quantity": qty,
                    "subtotal": Decimal(str(p["price"])) * qty
                })
        return result
    finally:
        if own_conn:
            conn.close()


def get_cart_total():
    return sum(
        (item["subtotal"] for item in get_cart_items()),
        Decimal("0.00")
    )


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    try:
        quantity = int(request.form.get("quantity", "1"))
        if quantity < 1:
            raise ValueError
    except ValueError:
        flash("Please enter a valid quantity.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT stock FROM products WHERE id=%s", (product_id,))
            product = cursor.fetchone()
        if not product:
            flash("Product not found.")
            return redirect(url_for("home"))
        current = int(session.get("cart", {}).get(str(product_id), 0))
        if current + quantity > int(product["stock"]):
            flash("Requested quantity exceeds available stock.")
            return redirect(url_for("home"))
        cart = session.get("cart", {})
        cart[str(product_id)] = current + quantity
        session["cart"] = cart
        flash("Product added to cart.")
    finally:
        conn.close()
    return redirect(url_for("home"))


@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    try:
        quantity = int(request.form.get("quantity", "0"))
        if quantity < 0:
            raise ValueError
    except ValueError:
        flash("Invalid quantity.")
        return redirect(url_for("home"))

    cart = session.get("cart", {})
    if quantity == 0:
        cart.pop(str(product_id), None)
    else:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT stock FROM products WHERE id=%s", (product_id,))
                product = cursor.fetchone()
            if not product or quantity > int(product["stock"]):
                flash("Quantity exceeds available stock.")
                return redirect(url_for("home"))
        finally:
            conn.close()
        cart[str(product_id)] = quantity
    session["cart"] = cart
    return redirect(url_for("home"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = get_cart_items()
    if not items:
        flash("Your cart is empty.")
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        email = request.form.get("customer_email", "").strip()
        if not name or len(name) > 150 or "@" not in email or len(email) > 255:
            flash("Enter a valid name and email address.")
            return redirect(url_for("checkout"))

        conn = get_db_connection()
        try:
            conn.begin()
            with conn.cursor() as cursor:
                cart = session.get("cart", {})
                product_ids = sorted(int(pid) for pid in cart)
                total = Decimal("0.00")
                locked = {}

                for pid in product_ids:
                    cursor.execute(
                        "SELECT id, name, price, stock FROM products WHERE id=%s FOR UPDATE",
                        (pid,)
                    )
                    product = cursor.fetchone()
                    qty = int(cart[str(pid)])
                    if not product or qty < 1 or qty > int(product["stock"]):
                        conn.rollback()
                        flash("Stock changed. Please review your cart.")
                        return redirect(url_for("home"))
                    locked[pid] = (product, qty)
                    total += Decimal(str(product["price"])) * qty

                cursor.execute(
                    "INSERT INTO orders (customer_name, customer_email, total_amount, status) "
                    "VALUES (%s, %s, %s, %s)",
                    (name, email, total, "Placed")
                )
                order_id = cursor.lastrowid

                for pid, (product, qty) in locked.items():
                    cursor.execute(
                        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                        "VALUES (%s, %s, %s, %s)",
                        (order_id, pid, qty, product["price"])
                    )
                    cursor.execute(
                        "UPDATE products SET stock = stock - %s WHERE id = %s AND stock >= %s",
                        (qty, pid, qty)
                    )
                    if cursor.rowcount != 1:
                        raise RuntimeError("Stock update failed")

            conn.commit()
            session["cart"] = {}
            return render_template_string("""
              <html><head><title>Order placed</title></head>
              <body style="font-family:Arial;background:#f3f5f9;padding:40px">
                <h1>Order placed successfully!</h1>
                <p>Order ID: {{ order_id }}</p>
                <p>Total: ₹{{ "%.2f"|format(total) }}</p>
                <a href="/">Back to Sahil Store</a>
              </body></html>
            """, order_id=order_id, total=total)
        except Exception:
            conn.rollback()
            app.logger.exception("Order placement failed")
            flash("Unable to place order. Please check application logs.")
            return redirect(url_for("checkout"))
        finally:
            conn.close()

    return render_template_string("""
      <!doctype html><html><head><meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Checkout - Sahil Store</title>
      <style>body{font-family:Arial;background:#f3f5f9;padding:30px}
      .panel{max-width:600px;margin:auto;background:white;padding:25px;border-radius:12px}
      input{display:block;width:100%;padding:12px;margin:8px 0 18px}
      button{background:#2563eb;color:white;border:0;padding:12px;border-radius:7px}
      </style></head><body><div class="panel">
      <h1>Checkout</h1>
      {% for message in get_flashed_messages() %}<p>{{ message }}</p>{% endfor %}
      {% for item in items %}<p>{{ item.name }} × {{ item.quantity }} — ₹{{ "%.2f"|format(item.subtotal) }}</p>{% endfor %}
      <h3>Total: ₹{{ "%.2f"|format(total) }}</h3>
      <form method="post">
        <label>Customer name</label><input name="customer_name" maxlength="150" required>
        <label>Email</label><input name="customer_email" type="email" maxlength="255" required>
        <button type="submit">Place Order</button>
      </form><p><a href="/">Back to store</a></p>
      </div></body></html>
    """, items=items, total=sum((i["subtotal"] for i in items), Decimal("0.00")))


@app.route("/db-test")
def db_test():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS db_name")
            db_name = cursor.fetchone()["db_name"]
        return f"<h1>Database Connected Successfully!</h1><p>Database: {db_name}</p><p><a href='/'>Back to Store</a></p>"
    except Exception:
        app.logger.exception("Database connection failed")
        return "Database connection failed. Check application logs.", 500
    finally:
        conn.close()


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



