# Costos del punto 6

Fuente pública: pestaña Costos, gid 1070657893, del Google Sheets indicado por el usuario. El CSV de origen y la copia normalizada se incluyen para trazabilidad y funcionamiento sin red. El servidor consulta la fuente con caché de cinco minutos y conserva la copia incorporada si la consulta falla. El botón Actualizar planilla vacía esta caché sin modificar los parámetros del simulador.

Se incluyen sólo filas cuyo Costo para producto sea exactamente Aplica (sin distinguir mayúsculas). Cada ID se cuenta una vez. Los importes son totales de línea publicados en CLP: no se multiplican por Cantidad ni por número de mallas. Vacíos y guiones se representan como null; los subtotales indican las partidas pendientes. La diferencia comparable suma únicamente filas con ambos valores. No se recalculan descuentos ni se usan los costos IFC como sumandos.

La vista inicial corresponde a Producto 80 kW: 103 partidas; 64 vinculadas a capas IFC, 35 en categorías sin geometría y 4 sin capa. La copia inicial contiene 222 partidas Aplica de 641 registros; las referencias de 10 kW se filtran separadamente. Los vínculos fuente se respetan, incluso cuando el nombre de una partida podría sugerir otra capa. Las asignaciones de campos vacíos se guardan localmente, sin escribir en Google Sheets, y se incluyen al exportar HTML y CSV. No se interpreta este presupuesto de otro proyecto como cotización validada por unidad del modelo D14 × H14.

## Vista por capa y paquete

Los indicadores, el gráfico, la tabla y el CSV utilizan la misma selección de referencia, capa, paquete y búsqueda. Al seleccionar una capa, el gráfico desglosa sólo sus paquetes; al seleccionar un paquete, desglosa las actividades que lo componen. La tabla mantiene visibles las descripciones de actividad. El HTML exportado conserva esta selección.

La vista derecha utiliza exactamente las mismas mallas y materiales IFC que el punto 5, con una cámara independiente. Filtra por el nombre de capa y no cambia la visibilidad ni el giro del visor principal. Las categorías comerciales sin geometría muestran un estado sin modelo. No se infieren cambios de costo por ocultar o girar geometría.

El desglose visual utiliza una dona con selector de base vigente/anterior. Cada sector representa su participación en los importes positivos disponibles de esa base; las partidas sin importe no generan sectores. El detalle conserva ambos presupuestos y se pagina en grupos de seis elementos. El botón Atrás permite volver de actividades a paquetes conservando la capa, y de paquetes a todas las capas. La tabla y los subtotales mantienen los registros y valores originales.

## Trazabilidad y cantidades

El nivel de navegación se conserva en el HTML descargado: panorama (azul), capa (verde), paquete (ámbar), actividad (violeta). La ruta superior y el botón Atrás permiten retroceder sin perder el contexto. Las fichas de actividad identifican ID y fila fuente y no atribuyen una partida a una pieza IFC individual.

La tabla conserva Criterio y Cantidad, normaliza HH/hh y muestra unitarios calculados como importe / cantidad publicada sólo cuando cantidad > 0. El unitario anterior es un equivalente con la misma cantidad fuente, no una tarifa histórica validada. Los importes originales no se recalculan. Los porcentajes vigente y anterior tienen denominadores independientes: total disponible de la selección; en la ficha de una actividad, total del paquete. La variación usa (vigente − anterior) / anterior sólo cuando anterior > 0. Cantidades y valores ausentes permanecen pendientes. Se suman horas declaradas sólo en filas HH; no se suman cantidades físicas de insumos de unidades distintas. El CSV incluye criterio, cantidad numérica, unitarios, porcentajes y sus denominadores para auditoría.

## Geometría V5

La geometría activa de los puntos 5/6 procede del HTML V80 v5, con variantes A/B. El v4 permanece archivado. Los nombres canónicos de capa se conservan para enlazar los presupuestos de la planilla; la capa original del HTML aparece en cada ficha. La ausencia de anillo en A se muestra como ausencia de geometría, sin borrar partidas presupuestarias. Cambiar a B actualiza la imagen, no recalcula ni reemplaza presupuestos. Las fichas de costeo del HTML v5 se identifican por separado.

## Grupos rotor, torre y fundación

Los botones del punto 5 y los tres KPI del punto 6 comparten `turbineLayerGroup`, evitando diferencias entre aislamiento geométrico y costos. Rotor agrupa las capas Rotor: … y Tren de potencia. Torre comprende exactamente Torre: montantes y riostras, Pernos y fijaciones de torre, Placas y conexiones de torre y Cabezal y soportes nuevos. Fundación incluye exclusivamente Fundación y morteros. Las demás categorías de fuente no se reasignan automáticamente.

Las tres tarjetas de rotor, torre y fundación aparecen únicamente en la vista completa: todas las capas seleccionadas, sin filtro de paquete, actividad ni búsqueda. Se ocultan al aislar un conjunto, una capa o cualquier selección parcial; los KPI financieros generales se conservan. El encabezado Panorama de costos se elimina y el selector CLP/USD permanece en una barra discreta. Las tarjetas usan tonos neutros y una altura reducida aproximadamente un 35 %.

Los KPI utilizan el contexto de capas del gráfico del punto 6 y la base de comparación activa (costo al detalle o costo por mayor). La cifra se convierte a USD con el tipo de cambio seleccionado; el porcentaje divide el importe disponible del grupo por el total disponible de esa selección. Se indica cualquier costo fuera de los tres grupos para explicar porcentajes que no sumen 100 %. Las filas pendientes permanecen pendientes; un grupo sin partidas en el alcance se muestra en cero, y un grupo con partidas sin importes se muestra Sin dato. Cada fila se cuenta una sola vez. El HTML exportado respeta la visibilidad de las tarjetas según la selección; el resumen de grupos permanece en el JSON de auditoría.

El encabezado del punto 6 agrupa fuente, acciones y tipo de cambio en una misma barra adaptable. El KPI Costo por potencia, junto a Comparación, usa el costo por mayor disponible de la selección dividido por la potencia de referencia fija de 80 kW (0,08 MW): USD/kW = CLP por mayor / dólar / 80; USD/MW = CLP por mayor / dólar / 0,08. Se actualiza con filtros y tipo de cambio. Los costos pendientes conservan la indicación de subtotal parcial; no es un indicador de energía ni USD/MWh.

Al aislar un conjunto completo desde el modelo, el título del punto 6 identifica rotor, torre o fundación y morteros. La vista completa, los filtros ordinarios y las selecciones parciales conservan Costos de la turbina y sus capas. Los cinco KPI financieros usan superficies neutras y espaciado reducido aproximadamente un 20 %, conservando la señal de base activa.
