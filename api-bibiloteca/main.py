"""API de la Biblioteca: gestiona libros con FastAPI y los guarda en un JSON."""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

logger = logging.getLogger("biblioteca")

# Ruta fija junto a main.py, sin importar desde dónde se ejecute
RUTA_DATOS = Path(__file__).parent / "datos" / "libros.json"

app = FastAPI(title="API de la Biblioteca")


# ---------- Modelos ----------
class LibroEntrada(BaseModel):
    titulo: str = Field(min_length=3, max_length=100)
    autor: str = Field(min_length=3, max_length=60)
    anio: int = Field(ge=1000, le=2100)
    disponible: bool = True


class LibroParcial(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=100)
    autor: str | None = Field(default=None, min_length=3, max_length=60)
    anio: int | None = Field(default=None, ge=1000, le=2100)
    disponible: bool | None = None


class Libro(LibroEntrada):
    id: int


# ---------- Persistencia ----------
libros: list[dict] = []
proximo_id = 1


def guardar() -> None:
    """Escribe la lista de libros en datos/libros.json."""
    RUTA_DATOS.parent.mkdir(parents=True, exist_ok=True)
    with open(RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(libros, f, ensure_ascii=False, indent=2)
    logger.info("Guardados %d libros", len(libros))


def cargar() -> None:
    """Carga los libros del archivo; si falta o está dañado, arranca vacía."""
    global libros, proximo_id
    libros = []
    try:
        with open(RUTA_DATOS, encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, list):
            libros = [Libro(**d).model_dump() for d in datos]
    except (OSError, ValueError, TypeError):
        logger.warning("Archivo de datos ausente o dañado: arranca vacía")
        libros = []
    libros.sort(key=lambda x: x["id"])
    proximo_id = max((l["id"] for l in libros), default=0) + 1


cargar()


def buscar_libro(libro_id: int) -> dict:
    for libro in libros:
        if libro["id"] == libro_id:
            return libro
    raise HTTPException(status_code=404, detail="Libro no encontrado")


# ---------- Endpoints ----------
@app.get("/", summary="Mensaje de bienvenida")
def raiz():
    """Devuelve el mensaje de la API."""
    return {"mensaje": "API de la biblioteca"}


@app.get("/libros", response_model=list[Libro], summary="Listar libros")
def listar_libros(
    autor: str | None = None,
    disponible: bool | None = None,
    desde: int = Query(0, ge=0),
    limite: int = Query(100, ge=0),
):
    """Lista libros con filtros (autor, disponible) y paginación."""
    resultado = libros
    if autor is not None:
        resultado = [l for l in resultado if l["autor"].lower() == autor.lower()]
    if disponible is not None:
        resultado = [l for l in resultado if l["disponible"] == disponible]
    return resultado[desde : desde + limite]


# Rutas fijas ANTES de /libros/{libro_id}
@app.get("/libros/buscar", response_model=list[Libro], summary="Buscar por texto")
def buscar(texto: str):
    """Busca texto en titulo o autor, sin distinguir mayúsculas."""
    t = texto.lower()
    return [l for l in libros if t in l["titulo"].lower() or t in l["autor"].lower()]


@app.get("/libros/estadisticas", summary="Estadísticas")
def estadisticas():
    """Devuelve total, disponibles y prestados."""
    disp = sum(1 for l in libros if l["disponible"])
    return {"total": len(libros), "disponibles": disp, "prestados": len(libros) - disp}


@app.post("/libros", response_model=Libro, status_code=201, summary="Crear libro")
def crear_libro(datos: LibroEntrada):
    """Crea un libro nuevo; 409 si ya existe mismo titulo y autor."""
    global proximo_id
    for l in libros:
        if (
            l["titulo"].lower() == datos.titulo.lower()
            and l["autor"].lower() == datos.autor.lower()
        ):
            raise HTTPException(status_code=409, detail="El libro ya existe")
    nuevo = {"id": proximo_id, **datos.model_dump()}
    proximo_id += 1
    libros.append(nuevo)
    guardar()
    logger.info("Libro creado con id %d", nuevo["id"])
    return nuevo


@app.get("/libros/{libro_id}", response_model=Libro, summary="Obtener libro")
def obtener_libro(libro_id: int):
    """Devuelve un libro por id."""
    return buscar_libro(libro_id)


@app.put("/libros/{libro_id}", response_model=Libro, summary="Reemplazar libro")
def reemplazar_libro(libro_id: int, datos: LibroEntrada):
    """Reemplaza todos los campos de un libro."""
    libro = buscar_libro(libro_id)
    libro.update(datos.model_dump())
    guardar()
    return libro


@app.patch("/libros/{libro_id}", response_model=Libro, summary="Actualizar parcial")
def actualizar_libro(libro_id: int, datos: LibroParcial):
    """Actualiza solo los campos enviados."""
    libro = buscar_libro(libro_id)
    cambios = datos.model_dump(exclude_unset=True)
    if any(v is None for v in cambios.values()):
        raise HTTPException(status_code=422, detail="Los campos no pueden ser null")
    libro.update(cambios)
    guardar()
    return libro


@app.delete("/libros/{libro_id}", status_code=204, summary="Borrar libro")
def borrar_libro(libro_id: int):
    """Borra un libro; responde 204 sin cuerpo."""
    libro = buscar_libro(libro_id)
    libros.remove(libro)
    guardar()
    return Response(status_code=204)


@app.post("/libros/{libro_id}/prestar", response_model=Libro, summary="Prestar libro")
def prestar(libro_id: int):
    """Marca el libro como no disponible."""
    libro = buscar_libro(libro_id)
    if not libro["disponible"]:
        raise HTTPException(status_code=409, detail="El libro ya está prestado")
    libro["disponible"] = False
    guardar()
    return libro


@app.post("/libros/{libro_id}/devolver", response_model=Libro, summary="Devolver libro")
def devolver(libro_id: int):
    """Marca el libro como disponible."""
    libro = buscar_libro(libro_id)
    if libro["disponible"]:
        raise HTTPException(status_code=409, detail="El libro ya está disponible")
    libro["disponible"] = True
    guardar()
    return libro
