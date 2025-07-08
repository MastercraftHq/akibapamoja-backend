# 💼 ChamaLink - Backend API

**ChamaLink** is a backend REST API built with Django and Django REST Framework, designed to digitize and streamline the management of *chamas* (informal 
savings/investment groups) in Kenya.


# AkibaPamoja Backend Setup Instructions
1. Clone the repo (do not fork) by running git clone https://github.com/Akiba_backend/

2. Create a .env file at the root folder (same location as manage.py file)

3. Create a virtual environment folder outside the github local repo NB: You may create the virtual environment folder inside the github local repo but you have to update the .gitignore to ignore the folder

4. Activate your virtual environment

5. Install packages by running pip install -r requirements.txt

6. To start the local host server run python3 manage.py runserver

7. To run migrations run the command python3 manage.py migrate

8. Ensure you access the website via http://127.0.0.1:8000 so that session auth works correctly

# Contributing to the codebase
By default always create a new branch from dev i.e. git checkout -b feature/your_name
Once your work is done, push your code to remote branch and create PR
All merge conflicts are solved using git rebase to preserve linear history


## 🚀 Features

- 🧑‍🤝‍🧑 **User Management** – Signup, login, and role-based access (admin, treasurer, member)
- 🏘 **Group Management** – Create and manage chamas, invite and remove members
- 💰 **Transactions** – Record contributions, withdrawals, and view ledger
- 📊 **Reports** – Generate group financial summaries
- 📩 **Notifications** – Send SMS or push alerts for transactions and updates

---
