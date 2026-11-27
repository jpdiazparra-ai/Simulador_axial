# Modelo activo de 80 kW: ensamblaje IFC de SolidWorks

Fuente: `ENSAMBLE TURBINA 80KW_1.IFC`, copia exacta del archivo suministrado. SHA-256: `649e6574fcefc2376ea39cc44bfb8b52cb0e3ef8af579caa340697737b61fb90`. IFC2X3, SolidWorks 2021. Los puntos 5 y 6, las capturas y la descarga HTML utilizan `ifc_80kw_mesh.json`. El HTML V80 v5 y el IFC v4 permanecen como fuentes históricas.

Se convierten las 378 representaciones de IfcProduct, sin omisiones: 66 representaciones de palas, 81 de brazos, 204 de uniones, 25 de eje/buje y dos rodamientos. Las representaciones CAD no equivalen a cantidades de compra. Se conserva GUID, entidad IFC, nombre, ensamblaje, geometría y material de cada una. La clasificación usa la jerarquía IfcElementAssembly, no el nombre genérico de una extrusión aislada. El archivo contiene tres ensamblajes de pala NACA 0018 A1400.

Se convierten las coordenadas mundiales en metros y se rota el eje vertical Y del archivo a Z del visor. El eje de animación se obtiene del cuerpo cilíndrico del eje 12IN SCH80 y queda en (0,0). La envolvente de las palas mide aproximadamente D14,27 × H14,25 m; es una medición geométrica, no una nueva dimensión de cálculo aerodinámico. La cámara y el plano de referencia se encuadran a los límites reales del archivo. Las 376 representaciones del rotor giran; los dos rodamientos permanecen fijos.

Este IFC no contiene torre ni fundación y no proporciona property sets ni pesos, cantidades de compra, potencia nominal del generador o relación de caja. Se muestran Sin dato / No declarada; no se heredan los 400 kg por pala, los pesos de torre/fundación ni otras propiedades del HTML anterior. No se estiman pesos a partir del volumen CAD.

Las capas conservan los nombres canónicos para enlazar costos. Las partidas de la planilla se mantienen, incluidas torre y fundación: sus botones permiten consultar costos aunque el IFC no tenga mallas correspondientes, y el visor informa esa ausencia. Las combinaciones se conservan tanto en la aplicación como en la descarga HTML. La sustitución geométrica no modifica el estudio QBlade de D12 × H16 ni sus curvas.

Regeneración: `python tools/convert_ifc_80kw.py "data/ENSAMBLE TURBINA 80KW_1.IFC" --output data`, con IfcOpenShell 0.9.0.post1 y NumPy sólo durante la conversión. La aplicación y las descargas incorporan mallas y Three.js, sin requerir IfcOpenShell ni conexión. Auditoría: `ifc_80kw_audit.json` (metadatos, transformaciones y correspondencia de todas las representaciones).
