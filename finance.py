import sqlite3
import hashlib
from datetime import datetime

# Database Initialization
class FinanceDB:
    DB_FILE = "finance_manager.db"

    @staticmethod
    def connect():
        return sqlite3.connect(FinanceDB.DB_FILE)

    @staticmethod
    def initialize():
        conn = FinanceDB.connect()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS budgets (
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            budget REAL NOT NULL,
            PRIMARY KEY (username, category),
            FOREIGN KEY (username) REFERENCES users(username)
        )''')
        conn.commit()
        conn.close()

# User Authentication
class UserAuth:
    MAX_ATTEMPTS = 3

    def init(self):
        self.current_user = None
        FinanceDB.initialize()
        self.attempts = {}

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def validate_password(self, password):
        if len(password) < 8:
            return "Password must be at least 8 characters long."
        if not any(char.isdigit() for char in password):
            return "Password must contain at least one number."
        if not any(char.isupper() for char in password):
            return "Password must contain at least one uppercase letter."
        return None

    def register(self):
        username = input("Enter a username: ")
        password = input("Enter a password: ")
        validation_error = self.validate_password(password)
        if validation_error:
            print(validation_error)
            return

        conn = FinanceDB.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, self.hash_password(password)))
            conn.commit()
            print("Registration successful!")
        except sqlite3.IntegrityError:
            print("Username already exists.")
        finally:
            conn.close()

    def login(self):
        while True:
            print("\n1. Register")
            print("2. Login")
            choice = input("Choose an option: ")

            if choice == "1":
                self.register()
                continue

            username = input("Enter your username: ")
            password = input("Enter your password: ")

            # Check if the account is locked due to multiple failed attempts
            if username in self.attempts and self.attempts[username] >= self.MAX_ATTEMPTS:
                print("Your account is locked due to multiple failed login attempts.")
                return False

            conn = FinanceDB.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()

            if result and result[0] == self.hash_password(password):
                self.current_user = username
                self.attempts[username] = 0  # Reset the attempt counter after successful login
                print("Login successful!")
                return True
            else:
                print("Invalid username or password.")
                self.attempts[username] = self.attempts.get(username, 0) + 1
                if self.attempts[username] >= self.MAX_ATTEMPTS:
                    print("Your account is now locked due to too many failed attempts.")
                    return False

# Transaction Management
class TransactionManager:
    def init(self, username):
        # Ensure the username is passed and set correctly
        if not username:
            raise ValueError("Username is required.")
        self.username = username

    def add_transaction(self):
        amount = float(input("Enter amount: "))
        category = input("Enter category (e.g., Food, Rent): ")
        type_ = input("Enter type (Income/Expense): ").capitalize()
        date = input("Enter date (YYYY-MM-DD) or leave blank for today: ") or datetime.now().strftime("%Y-%m-%d")
        note = input("Add a note for this transaction (optional): ")

        # Check if username is valid
        if not self.username:
            print("Error: Username is missing. Please log in again.")
            return

        conn = FinanceDB.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transactions (username, amount, category, type, date, note) VALUES (?, ?, ?, ?, ?, ?)",
                       (self.username, amount, category, type_, date, note))
        conn.commit()
        conn.close()
        print("Transaction added successfully.")

    def view_transactions(self):
        conn = FinanceDB.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, amount, category, type, date, note FROM transactions WHERE username = ?", (self.username,))
        transactions = cursor.fetchall()
        conn.close()

        if transactions:
            print("\nYour Transactions:")
            for t in transactions:
                print(f"  ID: {t[0]} | Amount: {t[1]} | Category: {t[2]} | Type: {t[3]} | Date: {t[4]} | Note: {t[5]}")
        else:
            print("No transactions found.")

    def update_delete_transaction(self):
        self.view_transactions()
        transaction_id = int(input("Enter the transaction ID to update/delete: "))

        print("\n1. Update Transaction")
        print("2. Delete Transaction")
        choice = input("Choose an option: ")

        conn = FinanceDB.connect()
        cursor = conn.cursor()

        if choice == "1":
            amount = float(input("Enter new amount: "))
            category = input("Enter new category: ")
            type_ = input("Enter new type (Income/Expense): ").capitalize()
            date = input("Enter new date (YYYY-MM-DD): ")
            note = input("Enter new note: ")
            cursor.execute("UPDATE transactions SET amount = ?, category = ?, type = ?, date = ?, note = ? WHERE id = ? AND username = ?", 
                           (amount, category, type_, date, note, transaction_id, self.username))
            print("Transaction updated successfully.")
        elif choice == "2":
            cursor.execute("DELETE FROM transactions WHERE id = ? AND username = ?", (transaction_id, self.username))
            print("Transaction deleted successfully.")
        else:
            print("Invalid choice.")

        conn.commit()
        conn.close()

# Budget Management
class BudgetManager:
    def init(self, username):
        self.username = username

    def set_budget(self):
        category = input("Enter the category for the budget: ")
        amount = float(input("Enter the budget amount: "))

        conn = FinanceDB.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO budgets (username, category, budget) VALUES (?, ?, ?)",
                       (self.username, category, amount))
        conn.commit()
        conn.close()
        print("Budget set successfully!")

    def view_budgets(self):
        conn = FinanceDB.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT category, budget FROM budgets WHERE username = ?", (self.username,))
        budgets = cursor.fetchall()
        conn.close()

        if budgets:
            print("\nYour Budgets:")
            for category, budget in budgets:
                print(f"  - {category}: {budget:.2f}")
        else:
            print("No budgets set.")

# Main Application
if name == "main":
    print("Welcome to the Advanced Personal Finance Manager!")
    user_auth = UserAuth()

    if not user_auth.login():
        exit("Goodbye!")

    transaction_manager = TransactionManager(user_auth.current_user)
    budget_manager = BudgetManager(user_auth.current_user)

    while True:
        print("\nMenu:")
        print("1. Add Transaction")
        print("2. View Transactions")
        print("3. Update/Delete Transaction")
        print("4. Set/View Budget")
        print("5. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            transaction_manager.add_transaction()
        elif choice == "2":
            transaction_manager.view_transactions()
        elif choice == "3":
            transaction_manager.update_delete_transaction()
        elif choice == "4":
            print("\n1. Set Budget")
            print("2. View Budgets")
            sub_choice = input("Choose an option: ")

            if sub_choice == "1":
                budget_manager.set_budget()
            elif sub_choice == "2":
                budget_manager.view_budgets()
            else:
                print("Invalid choice!")
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice!")