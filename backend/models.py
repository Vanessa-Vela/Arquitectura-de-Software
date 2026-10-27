from typing import List, Optional, Union
from pydantic import BaseModel


class Perfil(BaseModel):
    nombre: Optional[str] = None
    nombre_de_perfil: str
    # con el Método 1 llegan como int, con el de respaldo pueden ser texto ("12,3 mil")
    seguidores: Optional[Union[int, str]] = None
    seguidos: Optional[Union[int, str]] = None
    total_publicaciones: Optional[Union[int, str]] = None
    biografia: Optional[str] = None


class Publicacion(BaseModel):
    codigo: str
    tipo: str
    url: str
    descripcion: Optional[str] = ""
    me_gusta: Optional[int] = None
    comentarios: Optional[int] = None
    imagen_url: Optional[str] = None


class Rasgo(BaseModel):
    clave: str          # apertura, responsabilidad, extraversion, amabilidad, neuroticismo
    nombre: str
    puntaje: int        # 0 a 100
    nivel: str          # Bajo, Medio, Alto
    evidencia: str


class BigFive(BaseModel):
    rasgos: List[Rasgo]
    resumen: str
    estilo_comunicacion: str
    fortalezas: List[str]
    limitaciones: str
    metodo: str         # "gemini" o "heuristico"
    modelo: Optional[str] = None


class Analisis(BaseModel):
    perfil: Perfil
    publicaciones: List[Publicacion]
    bigfive: BigFive
    origen: str         # "cache" o "scraping"
