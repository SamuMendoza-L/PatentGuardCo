# Ingeniería de software y diagnóstico CMMI — PatentGuard CO

**Fecha:** 12 de noviembre de 2026  
**Alcance:** evolución documentada entre Trabajo 1 y Trabajo 2, código actual y suite de pruebas de PatentGuard CO.  
**Nota metodológica:** este documento es un diagnóstico académico basado en evidencia del repositorio. No equivale a una evaluación oficial ni certificación CMMI.

## Síntesis

PatentGuard CO evolucionó de una API funcional con validación, datos abiertos y análisis ético asistido por IA hacia una versión con endurecimiento de entradas, control de detalles de error y pruebas no funcionales. El trabajo refleja un ciclo de construcción, verificación y mejora incremental compatible con el enfoque de ingeniería de software de Roger Pressman y con una adaptación ligera de SCRUM.

El diagnóstico razonable es una **posición objetivo de Nivel 2 — Gestionado**: hay planificación y artefactos concretos por iteración, requisitos implementados, control de versiones, pruebas repetibles y evidencia de resultados. El nivel no puede declararse formalmente alcanzado sin evidencia organizacional de gestión de proyectos, medición sostenida, gestión de proveedores y aplicación consistente en varios proyectos. Para aproximarse al Nivel 3 se requiere estandarizar procesos, plantillas y criterios de calidad que trasciendan este repositorio.

## Marco de Roger Pressman aplicado

Pressman describe la ingeniería de software como un marco adaptable que organiza comunicación, planificación, modelado, construcción y despliegue/retroalimentación. PatentGuard CO no documenta un proceso ceremonial completo, pero su evidencia permite mapear estas actividades de forma iterativa.

| Actividad de marco | Trabajo 1: construcción base | Trabajo 2: mejora y verificación | Evidencia actual |
| --- | --- | --- | --- |
| Comunicación | Se definió el problema ético de autoría frente a lucro, fuente de datos y usuarios de la API. | Se hizo explícita la necesidad de seguridad, rendimiento y estabilidad. | `README.md`, `docs/PatentGuard_Co.md`, `docs/05_uso_justificado_ia.md`. |
| Planificación | Se seleccionaron FastAPI, HTTPX, Pydantic, pytest y Gemini; se dividió el sistema en módulos. | Se priorizaron deuda técnica, endurecimiento y pruebas no funcionales. | Estructura de `app/`, commits “Fase 1” y “Fase 2”. |
| Modelado | Se definieron modelos de solicitud/respuesta y reglas de integridad. | Se ampliaron límites de entrada y métricas de procesamiento. | `app/schemas.py`, `app/validator.py`. |
| Construcción | Se implementaron rutas, cliente de datos abiertos, validador y servicio Gemini. | Se corrigieron dependencias, sanitización, ocultación de errores y pruebas de seguridad/concurrencia. | `app/*.py`, `tests/*.py`, `requirements.txt`. |
| Despliegue y retroalimentación | Se documentó ejecución local, `/docs` y pruebas. | Se registró evidencia de ejecución y riesgos para corrección posterior. | `docs/evidencia_ejecucion_pruebas.txt`, auditoría técnica Fase 3. |

### Ciclo iterativo entre Trabajo 1 y Trabajo 2

El primer trabajo resolvió el flujo de valor mínimo: recibir la disputa, consultar una fuente pública, validar hechos técnicos y producir una evaluación cualitativa con limitaciones. El segundo trabajo no añadió un caso de negocio distinto; elevó atributos de calidad del mismo flujo.

```text
Trabajo 1: requisitos funcionales → diseño modular → implementación → pruebas unitarias
       │
       ▼ retroalimentación (deuda técnica, riesgos y evidencia)
Trabajo 2: endurecimiento → pruebas de seguridad/rendimiento → evidencia de ejecución
       │
       ▼
Fase 3: auditoría, trazabilidad y plan de mejora
```

Esta secuencia es iterativa porque los resultados de prueba y los riesgos detectados alimentan requisitos posteriores: límites de entrada, no filtración de detalles internos, sanitización de la consulta y medición de tiempo. No debe interpretarse como desarrollo terminado: los hallazgos de auditoría vuelven a alimentar el siguiente incremento.

## Requerimientos no funcionales

| Atributo | Requisito concretado | Implementación/evidencia | Estado |
| --- | --- | --- | --- |
| Confiabilidad | Manejar fallos de red, HTTP y JSON sin caída no controlada. | Excepción `DatosAbiertosAPIError`, `timeout=10`, pruebas de timeout/HTTP/JSON. | Parcial: faltan reintentos y observabilidad. |
| Seguridad | No exponer secretos ni detalles internos; rechazar cargas malformadas. | `.gitignore`, `.env.example`, límites Pydantic, sanitización SoQL, pruebas de seguridad. | Parcial: faltan autenticación y límite de tasa. |
| Rendimiento | Evitar descargar todo el dataset y observar duración de procesamiento. | Filtro Socrata, `$limit=1`, `perf_counter`, prueba simulada de 25 solicitudes. | Parcial: no representa dependencias reales ni carga de producción. |
| Mantenibilidad | Separar responsabilidades y fijar dependencias. | Módulos por responsabilidad, `requirements.txt` con versiones fijas. | Aceptable: falta automatización de análisis estático y configuración coherente. |
| Usabilidad de API | Contrato JSON, ejemplos y documentación interactiva. | FastAPI/OpenAPI, Pydantic, README y documento técnico. | Aceptable para el alcance. |
| Privacidad/ética | No afirmar culpabilidad y declarar límites de la IA. | Prompt, respuesta de limitaciones y documentación. | Parcial: falta política de minimización, retención y aviso de privacidad. |

## Adaptación de SCRUM

Para un proyecto académico pequeño, SCRUM se aplica de manera ligera: el *backlog* se traduce en fases y cada fase entrega un incremento verificable. No hay evidencia de ceremonias formales, equipo multidisciplinario ni métricas de velocidad; por eso se describe como adaptación, no como implementación completa de Scrum.

| Elemento SCRUM | Aplicación observada | Mejora propuesta |
| --- | --- | --- |
| Product backlog | Funcionalidad API, datos abiertos, validación, Gemini, endurecimiento, pruebas no funcionales y auditoría. | Mantener ítems con criterio de aceptación, prioridad, riesgo y responsable. |
| Sprint/incremento | Trabajo 1 entrega flujo funcional; Trabajo 2 entrega calidad no funcional; Fase 3 entrega auditoría documental. | Definir duración, objetivo y “Definition of Done” por sprint. |
| Refinamiento | La deuda técnica detectada se convirtió en tareas concretas de Fase 1 y 2. | Revisar capacidad, dependencias externas y requisitos de privacidad antes de iniciar. |
| Revisión | Evidencia de `pytest` y documentación permiten revisar el incremento. | Demostración con criterios de aceptación, datos no sensibles y acta de revisión. |
| Retrospectiva | La corrección de deprecaciones y seguridad indica aprendizaje técnico. | Registrar qué funcionó, qué no, acciones y responsables con fecha. |

Una definición de terminado útil para futuros ítems debería exigir: código revisado, pruebas automáticas verdes, documentación actualizada, análisis de seguridad/privacidad proporcional al cambio y evidencia reproducible en CI.

## Calidad documental

La documentación cubre propósito, arquitectura, campos de datos abiertos, API, reglas de validación, pruebas y justificación del uso de IA. También conserva evidencia de la ejecución de pruebas. Esto es una fortaleza para evaluación académica y transferencia de conocimiento.

Aspectos a mejorar:

- Actualizar conteos históricos: `docs/05_uso_justificado_ia.md` conserva referencias iniciales a 18 pruebas, aunque el propio documento explica después el aumento a 24.
- Mantener `README.md` alineado con la documentación extensa y con el comando validado de ejecución.
- Incorporar decisiones de arquitectura (ADR) para autenticación, tratamiento de datos personales, elección de proveedor y modo degradado.
- Versionar un contrato OpenAPI exportado o verificar su compatibilidad en CI.
- Documentar entorno de despliegue, variables efectivamente usadas, retención de logs y procedimiento de rotación de secretos.

## Matriz de trazabilidad

La siguiente matriz relaciona requisitos observables con módulo y evidencia de prueba. “Parcial” significa que la prueba confirma una porción del requisito, no todo su comportamiento en producción.

| ID | Requisito | Módulo(s) | Prueba/evidencia | Estado |
| --- | --- | --- | --- | --- |
| RF-01 | Exponer servicio y estado básico en JSON. | `app/main.py` | `test_health_check_endpoint` | Cubierto |
| RF-02 | Recibir conflicto con solicitudes, descripción e inventores opcionales. | `app/schemas.py`, `app/main.py` | `test_analizar_conflicto_exitoso`, `test_analizar_conflicto_payload_invalido` | Cubierto |
| RF-03 | Consultar datos abiertos por número sin descargar el dataset completo. | `app/client_datos_abiertos.py` | `$where`, `$limit=1`; `test_consultar_patente_exitoso` | Parcial (sin integración real automatizada) |
| RF-04 | Informar ausencia de resultados y fallos de proveedor. | `app/client_datos_abiertos.py`, `app/main.py` | pruebas de no encontrado, HTTP, timeout y JSON inválido | Cubierto a nivel unitario |
| RF-05 | Validar obligatoriedad, trazabilidad, tipos, fechas y duplicados. | `app/validator.py` | seis pruebas de `test_validator.py` | Cubierto |
| RF-06 | Producir análisis Gemini estructurado sin sustituir la validación determinista. | `app/gemini_service.py`, `app/main.py` | éxito y JSON inválido de Gemini; documentación de uso responsable | Parcial (respuesta no se revalida localmente) |
| RF-07 | Degradar con limitaciones cuando Gemini no está disponible. | `app/main.py`, `app/gemini_service.py` | cuota, clave ausente y prueba de no filtración | Cubierto a nivel unitario/API |
| RNF-01 | Restringir tamaño de campos y rechazar tipos corruptos. | `app/schemas.py` | casos parametrizados de `test_security.py` | Parcial (sin máximo de cardinalidad) |
| RNF-02 | Evitar inyección SoQL básica. | `app/client_datos_abiertos.py` | `test_sanitiza_intento_de_inyeccion_soql` | Parcial (sanitización no sustituye parametrización nativa) |
| RNF-03 | No exponer clave o rutas internas en la respuesta HTTP. | `app/main.py` | `test_respuesta_no_filtra_secretos_ni_rutas_internas` | Cubierto a nivel de respuesta |
| RNF-04 | Mantener aislamiento con solicitudes concurrentes simuladas. | `app/main.py` | `test_analizar_conflicto_soporta_25_peticiones_concurrentes` | Parcial (mocks, no carga externa real) |
| RNF-05 | Proteger configuración sensible del repositorio. | `.gitignore`, `.env.example` | revisión estática y escaneo de contenido rastreado | Cubierto en el repositorio actual |

## Calidad y competitividad

En una disputa real, la calidad no consiste en declarar quién tiene razón. Consiste en que la plataforma sea confiable al recopilar, distinguir y presentar evidencia: que no confunda la ausencia de un campo con culpabilidad, que preserve las limitaciones de la fuente, que entregue respuestas consistentes y que mantenga disponibles los servicios bajo fallos previsibles.

Esto afecta directamente su competitividad. Una herramienta con validaciones reproducibles, trazabilidad de consultas, respuesta explicable y tratamiento responsable de datos puede apoyar mejor una revisión humana que una solución que solo genera texto persuasivo. A la vez, una caída bajo carga, una fuga de clave o la difusión de acusaciones con nombres reales destruirían esa confianza. La calidad técnica, la privacidad y la neutralidad son por tanto atributos de producto y diferenciadores, no costos accesorios.

Indicadores recomendados para gobernar esa calidad:

- porcentaje de ejecuciones de CI exitosas y cobertura de rutas de error;
- latencia p50/p95 y tasa de errores por datos abiertos y Gemini;
- número de solicitudes rechazadas por validación, autenticación y límite de tasa;
- tiempo de detección y revocación de secretos;
- porcentaje de respuestas IA válidas contra el esquema local;
- número de incidentes de datos personales, con objetivo de cero.

## Diagnóstico CMMI

### Nivel estimado: 2 — Gestionado (diagnóstico académico)

El proyecto muestra evidencias compatibles con prácticas gestionadas a escala de un trabajo académico: alcance por fases, control de versiones, requisitos expresados en documentación, pruebas repetibles, evidencia de resultados y correcciones derivadas de hallazgos. La gestión todavía depende de decisiones puntuales del proyecto y no de procesos organizacionales estandarizados; por ello, el diagnóstico no puede ser una calificación oficial.

| Dimensión | Fortalezas observadas | Debilidades / brecha hacia Nivel 3 |
| --- | --- | --- |
| Gestión de requisitos | Requisitos funcionales y de calidad descritos; trazabilidad básica a módulos/pruebas. | No hay backlog formal con cambios aprobados, prioridades, criterios de aceptación ni gestión de versiones de requisitos. |
| Planificación y seguimiento | Fases identificables y commits que separan endurecimiento/pruebas. | No se evidencia estimación, capacidad, riesgos, responsables, cronograma ni seguimiento cuantitativo. |
| Aseguramiento de calidad | Suite automatizada de 24 pruebas, *mocks* y evidencia textual de ejecución. | No hay CI, umbrales, cobertura, revisión independiente ni política de calidad aplicable a cambios futuros. |
| Gestión de configuración | Git, rama de trabajo, dependencias fijadas y `.gitignore` de secretos. | No hay estrategia de versiones, *tags*, baseline, SBOM, control de cambios de configuración o despliegue reproducible. |
| Medición | Métrica de tiempo por respuesta y resultado de pruebas. | No se recolectan/analizan métricas históricas de defectos, latencia, disponibilidad o seguridad. |
| Gestión de riesgos | Se identifican fallos externos, límites de IA y deuda técnica. | No existe registro de riesgos con probabilidad, impacto, propietario y plan de contingencia. |
| Procesos organizacionales | Hay patrones modulares y documentos reutilizables dentro del proyecto. | No hay proceso definido, capacitación, biblioteca de activos ni evaluación de adherencia entre proyectos. |

### Plan concreto para escalar hacia Nivel 3 — Definido

| Etapa | Acción | Entregable / criterio de salida | Horizonte sugerido |
| --- | --- | --- | --- |
| 1. Definir proceso | Crear guía breve de ciclo de vida: requisitos, diseño, desarrollo, revisión, pruebas, liberación e incidentes. | Proceso versionado y usado por el siguiente incremento. | 1 semana |
| 2. Estandarizar artefactos | Plantillas para historias/requisitos, criterios de aceptación, ADR, riesgo, caso de prueba y revisión de PR. | Al menos un ítem futuro usa cada plantilla relevante. | 1–2 semanas |
| 3. Trazabilidad viva | Mantener matriz requisito → diseño → código → prueba → evidencia en cada cambio. | CI o revisión bloquea cambios sin evidencia actualizada. | 2 semanas |
| 4. Calidad repetible | Añadir CI que ejecute pruebas, formato/lint, análisis de dependencias y escaneo de secretos. | Pipeline verde requerido para integrar cambios. | 2–3 semanas |
| 5. Medición y análisis | Definir tablero mínimo de pruebas, defectos, vulnerabilidades, latencia y disponibilidad. | Tendencias revisadas en retrospectiva y acciones registradas. | 3–4 semanas |
| 6. Gobierno de seguridad y datos | Establecer autenticación, gestión de secretos, privacidad, retención y respuesta a incidentes. | Revisión de amenaza y procedimiento de incidentes aprobados para el entorno. | 3–5 semanas |
| 7. Mejora organizacional | Revisar adherencia, capacitar colaboradores y actualizar proceso con lecciones aprendidas. | Retrospectiva y versión mejorada del proceso aplicadas en más de un incremento. | Continuo |

El resultado esperado del Nivel 3 no es más burocracia: es que la calidad observada en este proyecto pueda repetirse de forma predecible, comprobable y sostenible por cualquier integrante del equipo.

## Conclusión

PatentGuard CO presenta una evolución coherente: primero resolvió el flujo funcional y luego respondió a riesgos técnicos con validación, endurecimiento y pruebas no funcionales. Su madurez actual puede describirse académicamente como gestionada, con una base útil para formalizar prácticas. El siguiente salto de valor consiste en convertir buenas decisiones puntuales en un proceso definido: trazabilidad viva, CI, medición, gestión de riesgos, privacidad y seguridad operativa.
