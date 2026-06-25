# Creating Administrative Users

To create an administrative user, you can use the built-in admin creation script `scripts/create_admin.py`.

This script supports both **command-line flags** and an **interactive mode** (which prompts you securely for inputs, hiding the password as you type).

---

## 1. Running inside Docker (Recommended)

If you are running the project using Docker Compose, you can run the script inside the active `api` container.

### Option A: Interactive Mode (Prompts for inputs)
Run the following command, and the terminal will prompt you for the details:
```bash
docker compose -f docker/docker-compose.yml run --rm api python -m scripts.create_admin
```

### Option B: Command Line Arguments
You can supply all required fields directly as arguments:
```bash
docker compose -f docker/docker-compose.yml run --rm api python -m scripts.create_admin --phone "998991234567" --password "secureadminpass" --full-name "System Admin"
```

---

## 2. Running Locally (On Host Machine)

If you are running the database and application directly on your host machine:

1. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate
   ```
2. **Run the script**:
   * **Interactive mode**:
     ```bash
     python -m scripts.create_admin
     ```
   * **Arguments mode**:
     ```bash
     python -m scripts.create_admin --phone "998991234567" --password "secureadminpass" --full-name "System Admin"
     ```

*Note: The script reads the database configuration directly from your `.env` file.*
