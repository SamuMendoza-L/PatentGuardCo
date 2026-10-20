# PatentGuard CO

> API para evaluar la integridad de registros técnicos en disputas de autoría relacionadas con patentes.

## Tabla de contenido

- [Propósito y contexto](#propósito-y-contexto)
- [Alcance y consideraciones](#alcance-y-consideraciones)
- [Análisis de cumplimiento de la actividad](#análisis-de-cumplimiento-de-la-actividad)
- [Consideraciones de mejora](#consideraciones-de-mejora)
- [Arquitectura](#arquitectura)
- [Componentes](#componentes)
- [Campos de datos abiertos](#campos-de-datos-abiertos)
- [API disponible](#api-disponible)
- [Reglas de integridad](#reglas-de-integridad)
- [Flujo de procesamiento](#flujo-de-procesamiento)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Pruebas](#pruebas)
- [Configuración y ejecución](#configuración-y-ejecución)

---

## Propósito y contexto

PatentGuard CO centraliza la evaluación técnica de la evidencia asociada a una disputa de autoría. La aplicación analiza registros de trazabilidad —por ejemplo, datos de desarrollo, identificadores o *hashes* de código— para detectar inconsistencias objetivas y, de forma opcional, solicitar a Gemini un análisis cualitativo de la evidencia recibida.

El proyecto se apoya en la distinción entre:

| Concepto | Descripción |
| --- | --- |
| **Autoría** | Reconocimiento del vínculo entre una persona inventora o creadora y su contribución técnica. |
| **Explotación económica** | Gestión de licencias, cesiones y otros derechos patrimoniales vinculados a una invención. |

El objetivo es aportar trazabilidad y señales técnicas para una revisión humana informada, sin sustituir los procedimientos legales, administrativos o periciales aplicables.

## Alcance y consideraciones

- La API identifica inconsistencias de datos mediante reglas deterministas.
- La integración con Gemini genera una apreciación orientativa basada únicamente en el *payload* enviado.
- Los resultados no constituyen asesoría jurídica, prueba judicial ni dictamen vinculante.
- La consulta se realiza sobre el recurso público de patentes configurado en el cliente de `datos.gov.co`.
- Las credenciales se proporcionan por variables de entorno y nunca deben incluirse en el repositorio.

## Análisis de cumplimiento de la actividad

La actividad proponía construir una API REST que abordara una disputa de autoría de patentes mediante datos abiertos, validación de integridad, pruebas unitarias y un análisis asistido por Gemini. PatentGuard CO cumple estos elementos al transformar un problema ético —el posible desconocimiento de la autoría de un desarrollo frente al interés de explotación económica— en un flujo técnico verificable.

| Requerimiento de la actividad | Implementación lograda | Evidencia |
| --- | --- | --- |
| API REST funcional | FastAPI expone `GET /`, `GET /health` y `POST /analizar-conflicto`. | Respuestas JSON y documentación interactiva en `/docs`. |
| Consumo de datos abiertos | El cliente HTTPX consulta el recurso de patentes de `datos.gov.co` por el campo `solicitud`. | Se verificó la recuperación de la solicitud real `99020335` (*DISPOSITIVO ACUSTICO*). |
| Validación de integridad | Se validan campos obligatorios, campos recomendados, tipos, fechas, coherencia temporal, rangos de año y solicitudes duplicadas. | `app/validator.py` y sus pruebas unitarias. |
| Detección de inconsistencias | El resultado agrupa errores, advertencias y anomalías por registro. | El endpoint incorpora los hallazgos en `inconsistencias_tecnicas`. |
| Integración con Gemini | El servicio envía el contexto de la patente, las inconsistencias y los reclamantes a Gemini con salida JSON estructurada. | `app/gemini_service.py` y pruebas de éxito, cuota y JSON inválido. |
| Pruebas de software | La solución usa `pytest` con *mocks* para servicios HTTP y Gemini. | Suite ejecutada: **18 pruebas aprobadas**. |

### Resultados logrados

1. **Trazabilidad de la consulta.** La API recibe uno o varios números de solicitud, consulta el registro público y normaliza su información en una estructura común. Para el caso `99020335`, identifica al solicitante, el título, los inventores registrados y los datos originales usados en el análisis.
2. **Separación entre hechos y valoración.** Las reglas de `validator.py` producen hallazgos deterministas y auditables; Gemini solo realiza una interpretación cualitativa posterior. Esta separación evita que una respuesta de IA se presente como evidencia técnica o jurídica concluyente.
3. **Tratamiento del dilema ético.** El sistema reconoce que el solicitante o titular puede tener un interés patrimonial, mientras que el campo de inventor permite revisar el reconocimiento de las personas creadoras. El análisis no decide quién tiene razón: visibiliza vacíos de información y solicita soportes adicionales, como trazabilidad de desarrollo, contratos o cesiones.
4. **Manejo responsable de servicios externos.** Los errores de red de datos abiertos, la falta de clave Gemini, los límites de cuota y las respuestas no válidas se convierten en resultados controlados, sin detener la API.
5. **Calidad verificable.** Las pruebas cubren validación, cliente de datos abiertos, servicio Gemini y endpoint principal. Los servicios externos se simulan en las pruebas para que sean repetibles y no dependan de la red o de una clave real.

### Conclusión

PatentGuard CO no pretende resolver una disputa de propiedad intelectual ni reemplazar a una autoridad competente. Su aporte consiste en convertir una preocupación ética sobre **autoría versus lucro** en un proceso de calidad de software: consultar evidencia pública, verificar su consistencia, exponer las limitaciones y generar una evaluación orientativa. De este modo, la explotación económica no se asume como prueba de autoría, y la falta de datos de inventores se trata como una señal que requiere revisión humana y documental.

## Consideraciones de mejora

- **Dependencias reproducibles:** antes de una entrega o despliegue limpio, conviene alinear `requirements.txt` con el SDK que utiliza el código (`google-genai`) y fijar las versiones validadas en el entorno virtual.
- **Actualización de Pydantic:** la suite se ejecuta correctamente, pero muestra advertencias de deprecación en los campos de ejemplo y validación mínima de `schemas.py`. Su actualización evitará incompatibilidades futuras.
- **Cobertura funcional adicional:** puede añadirse una prueba de integración controlada para verificar el mapeo de la estructura real de `datos.gov.co`, manteniendo las pruebas unitarias sin conexión externa.

## Arquitectura

PatentGuard CO sigue una arquitectura de API en capas. FastAPI recibe las solicitudes, coordina las reglas de validación y, según el caso, integra servicios externos de datos abiertos y de IA.

```text
Cliente REST
    │
    ▼
FastAPI (app.main)
    ├── schemas.py              Validación de entrada y salida
    ├── validator.py            Reglas deterministas de integridad
    ├── gemini_service.py       Análisis cualitativo opcional
    └── client_datos_abiertos.py Consulta de recursos datos.gov.co
    │
    ▼
Respuesta JSON estructurada
```

## Componentes

| Componente | Responsabilidad |
| --- | --- |
| `app/main.py` | Crea la aplicación FastAPI y expone las rutas HTTP. |
| `app/config.py` | Centraliza valores de configuración disponibles para la aplicación. |
| `app/schemas.py` | Define los modelos Pydantic de solicitud y respuesta. |
| `app/validator.py` | Aplica reglas de integridad sobre los registros recibidos. |
| `app/gemini_service.py` | Encapsula la comunicación con Gemini y gestiona fallos externos. |
| `app/client_datos_abiertos.py` | Consulta y normaliza registros del recurso de patentes de `datos.gov.co` mediante HTTPX. |
| `tests/` | Contiene pruebas unitarias de validación y API. |

## Campos de datos abiertos

Al consultar un recurso de patentes en `datos.gov.co`, el cliente puede recibir las siguientes columnas. Algunos conjuntos de datos utilizan nombres alternativos para el mismo concepto; por ello, el servicio contempla ambas variantes cuando estructura el resultado.

| Columna en JSON (`datos.gov.co`) | Significado |
| --- | --- |
| `solicitud` | Identificador único de la solicitud de patente en el recurso consultado. |
| `titulo_resumen` / `titulo` | Título o nombre de la invención. |
| `solicitante` / `titular` | Persona natural o jurídica que ostenta el derecho patrimonial. |
| `inventor` / `inventores` | Persona o personas naturales reconocidas como creadoras. |
| `fecha_de_publicacion` | Fecha de publicación oficial en gaceta. |
| `tr_mite` | Tipo o estado del trámite administrativo publicado por el recurso. |

## API disponible

La documentación interactiva se publica automáticamente en `/docs` al ejecutar la aplicación.

### `POST /analizar-conflicto`

Evalúa la consistencia de un conjunto de registros y obtiene un análisis orientativo de Gemini cuando existe una clave configurada.

#### Solicitud

```json
{
  "numeros_solicitud": ["99020335"],
  "descripcion_conflicto": "Se solicita revisar la trazabilidad de autoría del dispositivo acústico publicado en el registro abierto.",
  "inventores_reclamantes": ["HENRY AZIMA", "JOERG PANZER"]
}
```

#### Respuesta

```json
{
  "status": "success",
  "resumen_procesamiento": {
    "solicitudes_consultadas": 1,
    "registros_encontrados": 1
  },
  "registros_encontrados": [
    {
      "numero_solicitud": "99020335",
      "titulo": "DISPOSITIVO ACUSTICO",
      "inventor": "HENRY AZIMA; JOERG PANZER"
    }
  ]
}
```

> El ejemplo emplea una solicitud publicada en el recurso de datos abiertos. Los campos adicionales, las inconsistencias y el análisis de Gemini dependen de la respuesta vigente del portal y de la configuración de `GEMINI_API_KEY`.

### `GET /health`

Comprueba que el servicio se encuentra disponible y devuelve un estado `ok`.

## Reglas de integridad

Las reglas actuales son deterministas y producen mensajes de inconsistencia auditables.

| Regla | Criterio | Resultado |
| --- | --- | --- |
| Campos obligatorios | `numero_solicitud` o `titulo` están ausentes o vacíos. | Error de integridad del registro. |
| Campos recomendados | `solicitante` o `inventor` están ausentes o vacíos. | Advertencia para revisión de trazabilidad. |
| Fechas y tipos | Fechas inválidas, orden temporal incoherente o tipos no esperados. | Anomalía de datos. |
| Solicitudes duplicadas | El mismo número aparece más de una vez en el conjunto evaluado. | Inconsistencia a nivel de dataset. |

Estas señales indican que la información requiere revisión. Por sí mismas, no demuestran la titularidad, la autoría ni una infracción de propiedad intelectual.

## Flujo de procesamiento

1. El cliente envía una disputa a `POST /analizar-conflicto`.
2. Pydantic valida la forma y los tipos de los datos de entrada.
3. El cliente consulta cada número de solicitud en el recurso de datos abiertos y normaliza el registro encontrado.
4. El validador revisa los campos requeridos, los recomendados, las fechas y los duplicados.
5. El servicio Gemini recibe el contexto y las inconsistencias encontradas. Si no hay una clave configurada o el servicio falla, se devuelve una respuesta controlada con sus limitaciones.
6. FastAPI devuelve una respuesta JSON con el resultado técnico y el análisis cualitativo disponible.

## Estructura del proyecto

```text
PatentGuard CO/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI y rutas
│   ├── config.py                # Variables de entorno
│   ├── client_datos_abiertos.py # Cliente HTTPX para datos.gov.co
│   ├── validator.py             # Reglas de integridad
│   ├── gemini_service.py        # Integración con Gemini
│   └── schemas.py               # Modelos Pydantic
├── docs/                        # Documentación del proyecto
├── tests/
│   ├── test_validator.py        # Pruebas de reglas
│   └── test_api.py              # Pruebas de endpoints con mocks
├── .env.example                 # Plantilla de configuración
├── requirements.txt
└── README.md
```

## Pruebas

La suite usa `pytest` y evita invocar servicios externos durante las pruebas de API mediante *mocks*.

| Archivo | Cobertura principal |
| --- | --- |
| `tests/test_validator.py` | Registros válidos, campos obligatorios, tipos, fechas y solicitudes duplicadas. |
| `tests/test_api.py` | Respuesta del endpoint de disputa y simulación del servicio Gemini. |
| `tests/test_client_datos_abiertos.py` | Consulta exitosa, ausencia de resultados y fallos HTTP, de red o JSON. |
| `tests/test_gemini_service.py` | Éxito, clave ausente, límite de cuota y respuesta JSON inválida. |

Ejecuta la suite con:

```bash
.venv/bin/pytest -v --tb=short
```

## Configuración y ejecución

1. Crea y activa un entorno virtual.
2. Instala las dependencias: `pip install -r requirements.txt`.
3. Copia `.env.example` a `.env` y completa los valores necesarios.
4. Inicia el servidor:

```bash
uvicorn app.main:app --reload --env-file .env
```

### Variables de entorno

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `GEMINI_API_KEY` | Para análisis con IA | Clave de acceso a Gemini. Sin ella, se devuelve un análisis basado en reglas. |

---

_Última actualización: 20 de octubre de 2026._
