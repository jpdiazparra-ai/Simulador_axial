# Simulador_axial

App Streamlit para simulacion axial y visualizacion tecnica.

## Ejecutar local

```bash
cd /Users/jonathan.diaz/Desktop/PILOTOS_ANA_WANT
streamlit run app.py
```

## Desplegar en Render

- `buildCommand`: `pip install -r requirements.txt`
- `startCommand`: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`


## Visualizador de resultados

Al iniciar `app.py`, la vista **Visualizador de resultados** compara la configuración actual con alternativas de número de palas y cuerda. Comparte el motor Cp–TSR, el control, el generador, las pérdidas y el Weibull del panel. Permite seleccionar potencia aerodinámica o eléctrica, explorar el rotor animado, sincronizar azimut y polar, descargar puntos CSV y exportar un HTML autónomo. Los archivos de la vista son `results_visualizer.py` y `assets/results_visualizer.html`.

En el panel lateral, **Límite operativo del rotor** permite activar un máximo de rpm (valor inicial: 30). Al iniciar en QBlade se activa con el máximo de 30 rpm del estudio. Al activarlo se recalculan TSR, potencia, torque y cargas en el motor común.

La energía se integra sobre el rango de viento configurado y muestra su cobertura de la distribución del sitio; no se renormaliza. El ranking conserva masa por pala y demás supuestos: no optimiza estructura ni costos. La animación representa una pala recta equivalente con ciclo cinemático ideal y polar genérica; no resuelve estela ni pérdida dinámica. La polar ilustrativa no alimenta el modelo de potencia. En el modo paramétrico, los resultados no proceden de QBlade.


## Base aerodinámica QBlade · V80

El panel izquierdo distingue **Modelo paramétrico** y **QBlade · V80 (HTML)**. El segundo carga los datos declarados QBlade del archivo `visualizador_resultados_V80.html` en `data/qblade_v80_reference.json`; no ejecuta ni replica el solver LLFVW. Su procedencia queda registrada en el JSON.

La referencia restringe el cálculo a D=12 m, H=16 m, NACA 0015, pala recta sin modificadores y las ocho combinaciones de palas/cuerda del estudio. Calcula los cuatro vientos disponibles (4, 6, 8, 10 m/s). Sigue la selección de puntos y la interpolación del HTML: serie azimutal coincidente, punto tabulado, ajuste parabólico interior o PCHIP; no extrapola fuera del intervalo de rpm. Usa el óptimo tabulado limitado por el máximo de rpm seleccionado.

La potencia del estudio es aerodinámica; el modelo aplica después las pérdidas y los límites del generador para obtener potencia eléctrica. Se conserva P=½ρDHV³Cp, λ=ωR/V y T=P/ω. No se reescala una geometría no simulada ni se multiplica la potencia por una razón de áreas para atribuirla a QBlade. Las series azimutales de la animación y la polar proceden del HTML cuando están disponibles; una serie ausente se muestra como ausente. Las cargas estructurales posteriores siguen siendo aproximaciones del simulador.

Validación: los 32 puntos de operación de palas/cuerda, con máximo de 30 rpm, se contrastaron contra el JavaScript original del HTML: coinciden rpm, potencia, Cp y torque. La energía se integra con el Weibull del panel sobre el rango disponible, por lo que no se equipara al indicador energético parcial del HTML ni a una producción anual completa.


## Controles dentro del HTML y análisis conectado

El visualizador incluye controles del modo V80 para configuración, límite de rpm, Weibull, transmisión, eficiencias, parámetros eléctricos, supuestos estructurales y límites de evaluación. La geometría y el perfil se mantienen dentro del estudio disponible. Los controles se abren con **Editar supuestos y límites** y actualizan una secuencia de seis pasos: configuración, operación, pala, límites/decisión, modelo IFC y costos. La fila operativa o un clic en las curvas sincroniza el viento con los indicadores, el rotor y la polar.

Dentro de Streamlit, `visualizer_bridge.py` valida los cambios y sincroniza los widgets del panel izquierdo mediante un componente bidireccional (`assets/visualizer_component/index.html`). Las vistas técnicas y exportaciones nativas se recalculan con esos mismos valores. El HTML descargado incorpora los datos y el motor JavaScript (`assets/qblade_model.js`), por lo que sus controles funcionan sin servidor. La descarga HTML del visualizador conserva esta versión interactiva y los parámetros actuales. Las instantáneas se conservan en el navegador cuando hay almacenamiento disponible y se pueden exportar como JSON.

La conversión eléctrica, cargas y energía del motor JavaScript se contrastaron con Python en 15 casos que varían transmisión, eficiencias, potencia nominal, rpm, torque, masa, resistencia y parámetros eléctricos: coincidieron 600 valores numéricos más los resultados energéticos. Los estados documentales RFP se conservan como referencia; cambiar parámetros no certifica cumplimiento ni genera evidencias de ensayos o planos.


## Presentación de la aplicación

El panel izquierdo inicia cerrado y puede abrirse o cerrarse con la flecha. Al cerrarlo, el contenido ocupa todo el ancho disponible en escritorio y móvil. Sus widgets conservan el estado compartido para los controles del visualizador. El encabezado superior es compacto, sin banner fotográfico ni títulos o botones de visualizador duplicados; la configuración y la descarga HTML se encuentran dentro del panel interactivo. Los estilos generales de esta presentación están en `assets/minimal_layout.css`.


## Secuencia de lectura QBlade V80

Al seleccionar QBlade, el espacio de trabajo presenta seis pasos con el mismo diseño y una única selección de configuración y viento:

1. **Qué configuración conviene**: curvas comparadas y ranking por energía eléctrica parcial, con los mismos supuestos.
2. **Qué entrega y cómo gira**: indicadores del punto seleccionado, curvas de potencia/Cp/pérdidas, rpm y balance de conversión.
3. **Cómo trabaja la pala**: rotor y polar juntos; Reynolds de la polar elegido a partir de la serie azimutal del punto cuando existe, sin inventar ciclos ausentes.
4. **Qué limita el diseño**: utilización normalizada de límites, evolución con el viento, márgenes y comparación de escenarios por energía/torque.
5. **Explora el modelo 3D del IFC**: torre Rev. W y rotor V80 v5 D14 × H14, cámara, capas, propiedades y animación independiente.
6. **Costos de la turbina y sus capas**: partidas Aplica de Google Sheets, filtro por capa y paquete, actividades, comparación vigente/anterior y geometría IFC correspondiente a la derecha.

Los gráficos de curvas permiten fijar el viento con un clic. Los parámetros, las tablas numéricas y los escenarios se despliegan sólo cuando se necesitan. En QBlade se omiten los antiguos resúmenes y paneles nativos duplicados; la documentación RFP se conserva en la vista histórica del modelo paramétrico y no interrumpe la lectura aerotécnica. El CSV contiene las magnitudes de rotor, generador, cargas, pérdidas y los principales supuestos. Las ecuaciones y los datos numéricos del motor no cambian con esta reorganización.


## Lectura visual de la pala

El paso 3 usa una vista en planta amplia con anillo azimutal de |CL|, flechas de viento y sustentación, selectores rápidos de rotor/viento y tarjeta lateral del punto de operación. El anillo se construye con la serie azimutal disponible y se mantiene separado de la animación para evitar redibujar elementos estáticos en cada cuadro. Los valores aerodinámicos y eléctricos se identifican por separado. La polar se muestra debajo a todo el ancho, con curva de referencia, trayectoria de una vuelta y aro que sigue la pala 1.

La zona roja compara |α| con el ángulo de máximo CL estático; no confirma separación dinámica. El estado «Impulsando/Oponiéndose al giro» utiliza el signo del esfuerzo tangencial de la serie importada. Cuando falta una serie a las rpm del caso, no se inventan fuerzas ni ángulos: el anillo queda neutro y la tarjeta indica la ausencia. La longitud de las flechas es ilustrativa y la forma de pala se amplía uniformemente ×1,6. El archivo `assets/rotor_visualization.js` concentra esta presentación, manteniendo intacto el motor de potencia.


## Inicio y datos incorporados

Cada sesión nueva comienza con **QBlade · V80 (HTML)** seleccionado en el panel izquierdo, usando la geometría del estudio D12 × H16, NACA 0015, 3 palas de cuerda 1 m y límite de 30 rpm. Se puede cambiar de modo durante la sesión; recalcular no restaura los parámetros iniciales. El panel lateral sigue comenzando cerrado.

El modelo 3D V80 v5 D14 × H14 se conserva por separado del estudio aerodinámico D12 × H16. El visor no transfiere las curvas de potencia entre geometrías. Los datos, procedencia y regeneración del modelo se documentan en [data/MODEL_V80_V5.md](data/MODEL_V80_V5.md). Three.js r158 y su licencia MIT se incorporan localmente, sin CDN. IfcOpenShell sólo se necesita para regenerar las mallas, no para ejecutar la aplicación.

Los costos se consultan en la pestaña Costos de la planilla pública indicada por el usuario, con caché de cinco minutos y botón de actualización. Si la consulta falla, se utiliza la copia incluida. Los filtros de referencia, capa, paquete y búsqueda controlan indicadores, gráficos, actividades y CSV; el HTML exportado conserva la selección. Los valores ausentes siguen pendientes, no equivalen a cero. La geometría derecha conserva las mallas IFC y no modifica el visor del punto 5. Ver [data/COST_REFERENCE.md](data/COST_REFERENCE.md).

Para ejecutar las pruebas: `python -m unittest discover -s tests -v`. Las pruebas de paridad del motor HTML requieren Node.js disponible.


## Modelo 3D V80 v5 activo

Los puntos 5 y 6 cargan la geometría del HTML V80 v5 suministrado, en lugar del IFC v4. La variante inicial A es la recomendada sin anillo; el selector también permite explorar B con anillo. Las palas son NACA 0018, 400 kg, y la transmisión declarada es 1:10. Los datos aerodinámicos QBlade D12 × H16 y los presupuestos de Google Sheets conservan su fuente y alcance propios. La procedencia, variantes, mapeo de capas y regeneración se documentan en [data/MODEL_V80_V5.md](data/MODEL_V80_V5.md).
