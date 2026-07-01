# CarStore API

A full-featured car store management system built with **Django 6.0.5** and **Django REST Framework**. Manages inventory, clients, repairs, and sales with PDF invoice generation.

---

## Features

- **Inventory Management** - Add, edit, delete cars with VIN validation and auto/manual stock numbering
- **Client Management** - Register clients with license validation and age verification
- **Repair Services** - Log repairs with costs, dates, and notes
- **Sales & Invoices** - Complete sales transactions with fillable PDF invoice generation
- **API Documentation** - Interactive Swagger UI
- **JWT Authentication** - Secure token-based authentication
- **Auto Stock Numbering** - Automatic sequential stock numbers for inventory

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Django 6.0.5 | Web framework |
| Django REST Framework | REST API |
| SimpleJWT | JWT authentication |
| PostgreSQL (Supabase) | Production database |
| drf-spectacular | OpenAPI schema + Swagger UI |
| django-cors-headers | CORS support |
| pypdf + reportlab | PDF invoice generation |
| python-dotenv | Environment variable management |
| gunicorn | Production WSGI server |

---

## Prerequisites

- Python 3.14 or higher
- PostgreSQL (optional, SQLite works for local development)
- pip / pipenv

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/ahmed-m-3bdullatif/CarStoreProject.git
cd CarStoreProject
```

### 2. Create a virtual environment

```bash
pip install pipenv
pipenv install
pipenv shell
```

Or using standard venv:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the existing `.env` file or create a new one:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=*
DATABASE_URL=postgresql://user:password@host:port/dbname
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SECRET_API_KEY=your-api-secret
ACCESS_TOKEN_LIFETIME_DAYS=1
REFRESH_TOKEN_LIFETIME_DAYS=30
```

> Leave `DATABASE_URL` empty to fall back to local SQLite.

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

### 6. Start the server

```bash
python manage.py runserver
```

Server running at: http://127.0.0.1:8000

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | Built-in default | Django secret key - **change in production** |
| `DEBUG` | `True` | Debug mode - **set to `False` in production** |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `DATABASE_URL` | Local SQLite | PostgreSQL connection string |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed CORS origins |
| `SECRET_API_KEY` | `OpenSesame` | Optional middleware API secret key |
| `ACCESS_TOKEN_LIFETIME_DAYS` | `1` | JWT access token lifetime in days |
| `REFRESH_TOKEN_LIFETIME_DAYS` | `30` | JWT refresh token lifetime in days |
| `DJANGO_SETTINGS_MODULE` | `CarStore.settings` | Django settings module path |

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register a new user (public) |
| POST | `/api/auth/login/` | Login (returns access + refresh tokens) |
| POST | `/api/auth/refresh/` | Refresh access token |

### Inventory

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/inventory/` | List cars (search with `?search=`) |
| POST | `/api/inventory/` | Add a new car |
| GET | `/api/inventory/{id}/` | Car details |
| PUT/PATCH | `/api/inventory/{id}/` | Update a car |
| DELETE | `/api/inventory/{id}/` | Delete a car |
| GET | `/api/inventory/get_available/` | List available (unsold) cars |
| GET | `/api/inventory/get_last_stock/` | Get the highest stock number |

### Clients

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/clients/` | List clients |
| POST | `/api/clients/` | Add a client |
| GET/PUT/PATCH/DELETE | `/api/clients/{id}/` | Client details, update, delete |

### Repairs

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/repairs/` | List repairs (filter with `?car_id=`) |
| POST | `/api/repairs/` | Add a repair |
| GET/PUT/PATCH/DELETE | `/api/repairs/{id}/` | Repair details, update, delete |

### Sales

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/sales/` | List sales |
| POST | `/api/sales/` | Create a sale |
| GET/PUT/PATCH/DELETE | `/api/sales/{id}/` | Sale details, update, delete |
| GET | `/api/sales/{id}/download_fillable_pdf/` | Download PDF invoice |

### Store Settings

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/settings/` | Get store settings |
| PUT | `/api/settings/` | Update store settings |
| GET | `/api/settings/get_stock_mode/` | Get stock numbering mode |
| PUT | `/api/settings/update_settings/` | Update name, address, and stock config |

### API Documentation

| Endpoint | Description |
|---|---|
| `/api/docs/` | Interactive Swagger UI |
| `/api/schema/` | OpenAPI schema (YAML/JSON) |

---

## Project Structure

```
CarStoreProject/
├── CarStore/               # Django project configuration
│   ├── settings.py         # Settings (reads from .env)
│   ├── urls.py             # Root URL configuration
│   ├── wsgi.py             # WSGI entry point
│   └── asgi.py             # ASGI entry point
├── store/                  # Store application
│   ├── models.py           # Data models
│   ├── serializers.py      # API serializers
│   ├── views.py            # API views
│   ├── urls.py             # API routes
│   ├── admin.py            # Admin panel registration
│   ├── middleware.py       # Optional Secret-Key middleware
│   └── migrations/         # Database migrations
├── templates/
│   └── invoice_template.pdf    # PDF invoice template
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
├── Pipfile                 # Pipenv manifest
└── manage.py               # Django CLI entry point
```

---

## Data Models

| Model | Description |
|---|---|
| `StoreSettings` | Singleton store configuration (name, address, stock mode) |
| `Client` | Client information with license and age validation |
| `CarInventory` | Car inventory with VIN validation and stock tracking |
| `Repair` | Repair records linked to a car |
| `Sale` | Sales transactions (auto-updates inventory) |

---

## Authentication & Security

- All API endpoints require `Authorization: Bearer <token>` header, except `/api/auth/register/`
- Login returns both access and refresh tokens
- Access token lifetime: 1 day (configurable)
- Refresh token lifetime: 30 days (configurable)
- **Optional**: Enable `TestingBlockMiddleware` in `settings.py` to add a `Secret-Key` header guard

---

## Development

### Enabling the Secret-Key Middleware (Optional)

Add the following line to the `MIDDLEWARE` list in `settings.py`:

```python
'store.middleware.TestingBlockMiddleware',
```

Then include `Secret-Key: your-secret-key` in every API request header.

### PDF Invoices

Invoices are generated using `templates/invoice_template.pdf` as a base fillable form. Fields are filled with `pypdf`, and data is overlaid using `reportlab`.

---

## License

This project is for educational purposes.
