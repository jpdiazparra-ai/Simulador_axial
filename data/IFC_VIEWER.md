> Archivo histórico del v4. El modelo activo en los puntos 5 y 6 es el HTML V80 v5; ver [MODEL_V80_V5.md](MODEL_V80_V5.md).

# Modelo IFC del punto 5

Fuente: `Torre_RevW_rotor_V80_v4_D14m_H14m.ifc`. SHA-256 y auditoría de piezas en `ifc_v80_v4_audit.json`. Las 633 representaciones se convierten en coordenadas mundiales y metros, sin omisiones. El eje vertical es Z. Las seis capas «Rotor: …» (45 piezas) giran alrededor de (0, 0); las otras 588 permanecen fijas. Los 400 pernos se incluyen y su capa comienza oculta.

Las dimensiones D14 × H14, cuerda 1,4 m, generador 100 kW y caja 1:8 son propiedades del diseño declarado. No se transfieren potencia ni energía del estudio QBlade D12 × H16. La sincronización opcional copia sólo rpm; la animación no calcula resistencia, aeroelasticidad, interferencias ni costos.

Para regenerar, instalar IfcOpenShell 0.9.0.post1 y NumPy en un entorno de conversión y ejecutar `python tools/convert_ifc_v80.py data/Torre_RevW_rotor_V80_v4_D14m_H14m.ifc`. La aplicación no requiere IfcOpenShell. Documentación: https://docs.ifcopenshell.org/ifcopenshell-python/geometry_processing.html

El HTML incluye mallas y Three.js r158 localmente para funcionar sin CDN; licencia MIT en `assets/vendor/THREE-LICENSE.txt`. El navegador necesita WebGL. Las propiedades IFC se muestran como texto y no se ejecutan instrucciones del archivo.
