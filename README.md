# 💼 AkibaPamoja- Backend API

**AkibaPamoja** is a backend REST API built with Django and Django REST Framework, designed to digitize and streamline the management of *chamas* (informal savings/investment groups) in Kenya.


## 🛠️ Setup Instructions

### 1. Clone the repository and navigate to the folder with the project.
  ```sql
    git clone https://github.com/MastercraftHq/akibapamoja-backend.git
    cd akibapamoja-backend.git
  ```

### 2. Create a virtual environment and activate it:
  ```sql
    For windows.
    python -m venv venv
    venv/Scripts/activate

    Others.
    python3 -m venv venv
    source venv/Scripts/activate - Git Bash
  ```

### 3. Install the required packages/libraries:
  ```sql
    pip install -r requirements.txt
  ```

### 4. Set Up Environment Variables
  - Copy .env.example and rename it to .env.
  - Open .env and fill in the required values, especially SECRET_KEY, DEBUG, and database credentials.
  - Generate a secure secret key:
  ```sql
    python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
### 5. Set Up PostgreSQL
5.1 Login to PostgreSQL:
  ```sql
    psql -U postgres
  ```
  - If it asks for a password, enter the one you set during installation.

5.2 Inside the PostgreSQL shell, run:
```sql
    -- Create the database
    CREATE DATABASE akiba;

    -- Create a dedicated user with a secure password
    CREATE USER akiba WITH PASSWORD 'akiba';

    -- Set recommended environment defaults for the user
    ALTER ROLE akiba SET client_encoding TO 'utf8';
    ALTER ROLE akiba SET default_transaction_isolation TO 'read committed';
    ALTER ROLE akiba SET timezone TO 'Africa/Nairobi';

    -- Grant full access to the new database
    GRANT ALL PRIVILEGES ON DATABASE akiba TO akiba;

    -- Exit psql
    \q

  ```
    
### 6.  Run Migrations
  ```sql
    python manage.py makemigrations
    python manage.py migrate
  ```

### 7. Start the Development Server    
  ```sql
    python manage.py runserver
  ```
  - The documentation is on [127.0.0.0:8000](http://127.0.0.1:8000/)

### 🤝 Contributing
 ```sql
    git checkout -b feature/your_name
    git add .
    git commit -m " Add <feature/your-name> - short description"
    git pull origin dev --rebase
    git push origin feature/<your-branch-name>
  ```
- Push your branch and open a Pull Request (PR).
- Use git rebase to resolve conflicts and maintain a clean commit history.


### 🚀 Features

- 🧑‍🤝‍🧑 **User Management** – Signup, login, and role-based access (admin, treasurer, member)
- 🏘 **Group Management** – Create and manage chamas, invite and remove members
- 💰 **Transactions** – Record contributions, withdrawals, and view ledger
- 📊 **Reports** – Generate group financial summaries
- 📩 **Notifications** – Send SMS or push alerts for transactions and updates

---
