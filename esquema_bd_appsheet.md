# Esquema de Base de Datos para AppSheet / Antigravity

Recomendación: Configura estas tablas en Google Sheets o en una base de datos SQL compatible (PostgreSQL/MySQL) y luego conéctalas a AppSheet.

## 1. Tabla: Trabajadores
Mantiene el registro biométrico e información del personal.
- `ID_Empleado` (Tipo: Text, Key: True, Descripción: Identificador único, ej. DNI)
- `Nombre_Completo` (Tipo: Text)
- `Cargo` (Tipo: Text)
- `Departamento` (Tipo: Text)
- `Foto_Referencia` (Tipo: Image, Descripción: Foto frontal para FaceNet)
- `Email_Contacto` (Tipo: Email)

## 2. Tabla: Eventos_SST
Almacena todas las detecciones de la IA a través del Webhook.
- `ID_Evento` (Tipo: Text, Key: True, Initial Value: `UNIQUEID()`)
- `Fecha_Hora` (Tipo: DateTime, Initial Value: `NOW()`)
- `ID_Empleado` (Tipo: Ref, Reference Table: Trabajadores)
- `ID_Camara` (Tipo: Text)
- `Metodo_Evaluacion` (Tipo: Enum, Values: [RULA, REBA, OWAS, EPP])
- `Puntuacion` (Tipo: Number)
- `Nivel_Riesgo` (Tipo: Enum, Values: [Leve, Medio, Alto, Critico])
- `Imagen_Evidencia` (Tipo: Image)
- `Estado_Revision` (Tipo: Enum, Values: [Pendiente, Descartado, Aprobado], Initial Value: `Pendiente`)
- `Acto_Admin_Generado` (Tipo: File)

## 3. Tabla: Tipos_Falta
Tipifica y estandariza los incidentes.
- `ID_Falta` (Tipo: Text, Key: True)
- `Descripcion` (Tipo: Text, Descripción: ej. "Ausencia de Casco", "Inclinación de tronco > 60 grados")
- `Gravedad_Base` (Tipo: Enum, Values: [Leve, Grave, Critica])
- `Metodo_Asociado` (Tipo: Enum, Values: [RULA, REBA, OWAS, EPP])
