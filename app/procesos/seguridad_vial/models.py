from pydantic import BaseModel
from typing import Optional

# Row 9 Column Indices (1-based for openpyxl)
class ExcelColumns:
    CEDULA = 2
    NOMBRE = 3
    ES_CONDUCTOR_LABORAL = 15
    RODAMIENTO = 16
    PLACA = 18
    ES_PROPIETARIO = 19
    IDENTIFICACION_PROPIETARIO = 21
    
    # RUNT Vehiculo
    VIN = 22
    MOTOR = 23
    MODELO = 24
    MARCA = 25
    CILINDRAJE = 26
    KILOMETRAJE = 27
    FECHA_MATRICULA = 28
    RTM_ESTADO = 29
    RTM_VENCIMIENTO = 30
    SOAT_ESTADO = 31
    SOAT_VENCIMIENTO = 32
    
    # RUNT Ciudadano
    LICENCIA_LABOR_CATEGORIA = 33
    CATEGORIA_ACTUAL = 34
    LICENCIA_VENCIMIENTO = 35
    LICENCIA_ESTADO = 36
    RESTRICCIONES = 37
    CUMPLIMIENTO = 38
    
    # SIMIT
    SIMIT_CODIGO = 40
    SIMIT_DESCRIPCION = 41
    SIMIT_FECHA = 42
    SIMIT_ESTADO = 43
    SIMIT_PAGO = 44
    
    # Metadata
    FECHA_REVISION = 45
    PROCESADO = 46

class ProcessRequest(BaseModel):
    es_conductor_laboral: str = "si"  # si / no
    rodamiento: str = "si"           # si / no
