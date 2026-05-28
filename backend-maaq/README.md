# Backend MAAQ

API Python/FastAPI para el TPS MAAQ conectado a SQL Server (`maaq_bd`).

## Inicio

```powershell
cd D:\Maaq\backend-maaq
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Edita `.env` con tu servidor SQL Server. La API queda en:

- `http://localhost:8000/api/health`
- `http://localhost:8000/docs`

## Modulos API

- `/api/catalogos`
- `/api/clientes`
- `/api/empleados`
- `/api/proyectos`
- `/api/equipos`
- `/api/socios`
- `/api/dashboard`

Todas las respuestas siguen el formato:

```json
{ "ok": true, "data": {}, "meta": {} }
```

## Nota sobre Cliente.Email

El script original define `Cliente.Email` como `nchar(10)`, insuficiente para correos reales.
Si deseas usar emails completos desde el frontend, ejecuta:

```sql
ALTER TABLE dbo.Cliente ALTER COLUMN Email varchar(100) NULL;
```

Tambien queda disponible en `db/patches/001_cliente_email.sql`.
