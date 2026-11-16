# API de la Biblioteca

API REST hecha con FastAPI para gestionar los libros de una biblioteca.
Permite crear, listar, actualizar y borrar libros, además de filtrar,
paginar y buscar. Los datos se guardan en `datos/libros.json`.

## Instalar

    python -m venv .venv
    source .venv/bin/activate    # En Windows: .venv\Scripts\activate
    pip install -r requirements.txt

## Correr

    uvicorn main:app --reload

Después abrí http://127.0.0.1:8000/docs para probar los endpoints.

## Endpoints

GET /, GET /libros, GET /libros/buscar, POST /libros, GET/PUT/PATCH/DELETE
/libros/{id}, POST /libros/{id}/prestar, POST /libros/{id}/devolver y
GET /libros/estadisticas.
