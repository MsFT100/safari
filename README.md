# Safari Django Backend

This is the backend service for the Safari project, built with Django and Django REST Framework. It includes integration with Pesapal for payments and uses Celery for asynchronous background tasks.

## Features

- User authentication (JWT, Social Login with Google)
- Pesapal payment integration
- Robust background task processing with Celery and Redis

---

## Prerequisites

- Python 3.8+
- Pip & Virtualenv
- Docker and Docker Compose (for running Redis)

---

## 1. Project Setup

### a. Clone the Repository

```bash
git clone <your-repository-url>
cd safari
```

### b. Create and Activate a Virtual Environment

```bash
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
```

### c. Install Dependencies

Install all the required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

### d. Configure Environment Variables

Create a `.env` file in the project root directory by copying the example file.

```bash
cp .env.example .env
```

Now, open the `.env` file and fill in your specific credentials and settings (Pesapal keys, Google client ID/secret, etc.).

### e. Apply Database Migrations

Run the following command to set up your database schema.

```bash
python manage.py migrate
```

---

## 2. Running the Application

To run the application, you need to start four separate processes in four different terminal windows: Redis, the Django server, the Celery worker, and the Celery beat scheduler.

### a. Start Redis

The simplest way to run Redis is using Docker.

```bash
docker run -d -p 6379:6379 redis
```

This command will download the Redis image (if you don't have it) and start a container in the background.

### b. Start the Django Development Server

This process runs the main web application.

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

### c. Start the Celery Worker

The worker process executes background tasks, such as verifying payments.

```bash
celery -A safari worker -l info
```

### d. Start the Celery Beat Scheduler

The beat process schedules periodic tasks, like the one that checks for pending transactions.

```bash
celery -A safari beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

*(Note: For the scheduler command to work, you need to run `pip install django-celery-beat` and add `'django_celery_beat'` to `INSTALLED_APPS` in your settings. For a simpler setup, you can omit the `--scheduler` flag).*
