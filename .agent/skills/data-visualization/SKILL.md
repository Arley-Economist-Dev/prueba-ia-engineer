---
name: data-visualization
description: Estándar de diseño y visualización de datos ejecutiva para tableros corporativos. Aplica máxima relación tinta-datos (Data-Ink Ratio), selección perceptual de gráficos y la paleta de identidad visual de Casa Pellas.
version: 1.0.0
---

# Reglas de Diseño de Visualizaciones (Casa Pellas AI Suite)

## 1. Paleta de Color Corporativa y Semántica
- Fondo estructural de gráficos: Transparente sobre tarjetas `#17217D` con bordes sutiles en `#1C376C`.
- Serie Primaria (Valores principales / Ventas / Existencias): `#FFFFFF` y `#18489B`.
- Serie Secundaria / Comparativas (Tránsito / Pedido): Gradiente `#18489B` hacia `#122092`.
- Alertas y Límites Críticos (Fuga, Quiebre, Modelos por descontinuar como RAV4): Resaltado ámbar/coral suave (`#FF7C5C` o `#E0A96D`) para destacar el punto de inflexión sin romper la armonía azul.
- Ejes, Retículas y Leyendas:
  * Cuadrículas (Grid): Opacidad mínima (`rgba(255, 255, 255, 0.08)`), sin líneas verticales superfluas.
  * Etiquetas de ejes: Texto en blanco con 70% de opacidad (`#FFFFFFB3`), fuente Inter o Roboto, tamaño 11px-12px.

## 2. Selección de Gráficos (Data-to-Ink Rules)
- Prohibiciones estrictas: Cero gráficos 3D, cero gráficos de pastel con más de 4 categorías, cero ejes truncados que distorsionen comparaciones de magnitud.
- Caso 1 (Inventarios y Pedidos Toyota):
  * Utilizar barras horizontales ordenadas de mayor a menor para comparar los 11 modelos, con marcadores visuales para el "Pedido Mínimo / Lote".
  * Incluir gráficos de cobertura mensual proyectada (Spline Area) mostrando la línea de seguridad recomendada.
- Caso 2 (Renovaciones Capesa):
  * Curva de Elasticidad de Contacto: Gráfico de línea suave (`stroke: { curve: 'smooth' }`) destacando con un marcador/anotación fija el punto T-20 días (estándar meta) vs T-3 días (realidad operativa).
  * Distribución de Carga Operativa: Gráfico Donut de una sola capa con métrica central numérica para contrastar el 12.6% de llamadas gastadas en pólizas Domiciliadas/Financiadas frente a Manuales.

## 3. Tooltips y Micro-interacciones (ApexCharts / Plotly.js)
- Formato de Tooltip: Tarjeta flotante con fondo `#122092`, borde `#1C376C`, sombra difusa (`box-shadow: 0 4px 20px rgba(0,0,0,0.5)`).
- Formateo estricto de valores: Separadores de miles y moneda en USD (`$#,##0`), porcentajes con un solo decimal (`0.0%`).
- Animaciones fluidas: Duración máxima de 400ms al cargar. Desactivar re-animación continua durante el movimiento de los sliders interactivos para evitar latencia (`dynamicAnimation: { enabled: false }`).

