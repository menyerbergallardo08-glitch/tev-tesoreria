# BACKLOG TÉCNICO Y OPERACIONAL DE PRODUCTO (V3.1)
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

---

### Clasificación de Tareas y Mejoras

---

### Grupo 1: Correcciones Recomendadas antes de Apertura (P2 / P3)

| ID | Tipo | Descripción | Problema | Impacto | Prioridad | Esfuerzo | Criterio de Aceptación | Estado |
|---|---|---|---|---|---|---|---|---|
| **PB-01** | CONTROL / UX | Máscara de entrada para comprobante SENIAT | Personal puede tipear menos o más de 14 dígitos | Error 422 al enviar formulario | **P2** | 2h | Input formatea automáticamente a 14 dígitos numéricos | PENDIENTE |
| **PB-02** | UX | Deshabilitar botones de submit tras 1er clic | Usuario impaciente hace doble clic rápido | Petición repetida bloqueada por backend | **P3** | 1h | Botón muestra spinner y se deshabilita hasta respuesta HTTP | PENDIENTE |
| **PB-03** | REPORTING | Exportador CSV / Imprimible de Cuadre Diario | Administradora requiere soporte físico | Dependencia de captura de pantalla | **P3** | 3h | Botón "Imprimir Cierre" genera vista limpia para impresora | PENDIENTE |

---

### Grupo 2: Mejoras Futuras / No Bloqueantes (P4)

| ID | Tipo | Descripción | Impacto | Prioridad | Esfuerzo | Criterio de Aceptación | Estado |
|---|---|---|---|---|---|---|
| **PB-04** | INTEGRATION | Conector API Profit Plus ERP | Facilita importación de facturas | **P4** | 16h | Endpoints de ingesta validados con Profit Plus | FUTURO |
| **PB-05** | ANALYTICS | Gráficos históricos de flujo de caja 30 días | Visibilidad gerencial avanzada | **P4** | 8h | Gráficos Chart.js interactivos en panel directivo | FUTURO |
