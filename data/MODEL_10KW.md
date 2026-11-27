# Proyecto 10 kW · IFC y análisis paramétrico

La pestaña «10 kW · IFC» es un espacio independiente del estudio V80. Su configuración se edita en el formulario propio y utiliza el mismo motor paramétrico Python de la aplicación, con `qblade_reference_mode=False`. No usa las curvas QBlade D12 × H16 para producir resultados de 10 kW.

## Procedencia geométrica

Fuente recibida: `B-ENSAMBLE FLUXIAL PLANTA.IFC`, IFC2X3 exportado desde SolidWorks. SHA-256: `57dbd6d89e6028c5f44e4dd924570dbf7ee5f9db4179523c75cbb1cba1702268`. El archivo original no se modifica. La aplicación consume `ifc_10kw_mesh.json`; no necesita IfcOpenShell en ejecución.

La conversión conserva 133 objetos geométricos con GUID, 26 ensamblajes y 94.890 triángulos, sin productos omitidos. Los 133 objetos no equivalen a 133 piezas físicas de compra. Las capas se clasifican por nombres de los ensamblajes antecesores; los nombres CAD genéricos se conservan en las fichas.

Se aplican las transformaciones mundiales del IFC y sus unidades mediante IfcOpenShell. El mástil identifica el eje vertical Z. Las envolventes dan aproximadamente 5,679 m de diámetro y 4,015 m de altura para los conjuntos de pala. Estas medidas incluyen el volumen geométrico exportado y requieren confirmar cotas de diseño. No se obtuvo una sección central continua para medir la cuerda; la cuerda de referencia es 0,8 m, confirmada por el usuario. El perfil NACA 0018 continúa como hipótesis editable. La cuerda puede variarse para escenarios de cálculo. Los cambios de cálculo no deforman el IFC.

El nombre «B-ASPA FRP 158KG TOTAL» aparece en tres ensamblajes. No hay propiedades estructuradas de masa que validen su alcance. La masa inicial de formulario de 158 kg no se aplica hasta que el usuario la active. Tampoco se muestran tensiones calculadas hasta activar las hipótesis estructurales y la masa.

## Alcance del cálculo

El generador de cálculo usa el catálogo existente GDG-860 de 10 kW, 70 rpm nominales. Esta ficha debe confirmarse frente al generador fluxial representado en el IFC. La potencia eléctrica se limita a 10 kW. El recurso Weibull inicial k=2 y c=6 m/s es un supuesto editable; la energía se integra entre 1 y 20 m/s, conservando la cobertura de ese intervalo.

El punto 1 compara la cuerda elegida y variantes de ±20 %. El punto 2 muestra operación, conversión y exportación CSV. El punto 3 muestra cinemática y una polar genérica; no extrapola Cl fuera del intervalo de la polar. El punto 4 compara con umbrales introducidos y no certifica resistencia ni fatiga. El punto 5 muestra exclusivamente la geometría suministrada, con selección, capas, encuadre y captura PNG. El HTML descargado incorpora datos, Three.js y geometría para abrirse sin conexión.

## Reconstrucción del activo

IfcOpenShell sólo es necesario para reconstruirlo:

```sh
python tools/convert_ifc_10kw.py '/ruta/B-ENSAMBLE FLUXIAL PLANTA.IFC' --output data
```

`ifc_10kw_audit.json` registra las medidas, métodos, capas y huella del archivo de origen.
