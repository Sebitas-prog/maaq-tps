USE maaq_db;
GO

IF OBJECT_ID('dbo.RRHH_Contrato', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RRHH_Contrato (
        IDcontrato int IDENTITY(1,1) NOT NULL,
        IDempleado int NOT NULL,
        CodigoContrato varchar(30) NOT NULL,
        Obra varchar(100) NOT NULL,
        Cargo varchar(80) NOT NULL,
        FechaInicio date NOT NULL,
        FechaFin date NOT NULL,
        SalarioDiario decimal(10,2) NOT NULL,
        Estado varchar(20) NOT NULL CONSTRAINT DF_RRHH_Contrato_Estado DEFAULT ('activo'),
        FechaLiquidacion date NULL,
        TotalLiquidacion decimal(12,2) NULL,
        FechaCreacion datetime NOT NULL CONSTRAINT DF_RRHH_Contrato_FechaCreacion DEFAULT (GETDATE()),
        CONSTRAINT PK_RRHH_Contrato PRIMARY KEY CLUSTERED (IDcontrato ASC),
        CONSTRAINT UQ_RRHH_Contrato_Codigo UNIQUE (CodigoContrato),
        CONSTRAINT FK_RRHH_Contrato_Empleado FOREIGN KEY (IDempleado) REFERENCES dbo.Empleado(IDempleado),
        CONSTRAINT CK_RRHH_Contrato_Fechas CHECK (FechaFin >= FechaInicio),
        CONSTRAINT CK_RRHH_Contrato_Salario CHECK (SalarioDiario >= 0),
        CONSTRAINT CK_RRHH_Contrato_Estado CHECK (Estado IN ('activo', 'renovado', 'liquidado'))
    );
END
GO

IF OBJECT_ID('dbo.RRHH_Asistencia', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RRHH_Asistencia (
        IDasistencia int IDENTITY(1,1) NOT NULL,
        IDempleado int NOT NULL,
        IDcontrato int NULL,
        Fecha date NOT NULL,
        Obra varchar(100) NOT NULL,
        Estado varchar(20) NOT NULL,
        Horas decimal(5,2) NOT NULL CONSTRAINT DF_RRHH_Asistencia_Horas DEFAULT (8),
        Extras decimal(10,2) NOT NULL CONSTRAINT DF_RRHH_Asistencia_Extras DEFAULT (0),
        Observacion varchar(250) NULL,
        FechaRegistro datetime NOT NULL CONSTRAINT DF_RRHH_Asistencia_FechaRegistro DEFAULT (GETDATE()),
        CONSTRAINT PK_RRHH_Asistencia PRIMARY KEY CLUSTERED (IDasistencia ASC),
        CONSTRAINT FK_RRHH_Asistencia_Empleado FOREIGN KEY (IDempleado) REFERENCES dbo.Empleado(IDempleado),
        CONSTRAINT FK_RRHH_Asistencia_Contrato FOREIGN KEY (IDcontrato) REFERENCES dbo.RRHH_Contrato(IDcontrato),
        CONSTRAINT CK_RRHH_Asistencia_Estado CHECK (Estado IN ('presente', 'tardanza', 'inasistencia', 'permiso', 'descanso')),
        CONSTRAINT CK_RRHH_Asistencia_Horas CHECK (Horas >= 0 AND Horas <= 24),
        CONSTRAINT CK_RRHH_Asistencia_Extras CHECK (Extras >= 0),
        CONSTRAINT UQ_RRHH_Asistencia_Dia UNIQUE (IDempleado, Fecha, Obra)
    );
END
GO

IF OBJECT_ID('dbo.RRHH_Destajo', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RRHH_Destajo (
        IDdestajo int IDENTITY(1,1) NOT NULL,
        IDempleado int NOT NULL,
        IDcontrato int NULL,
        Fecha date NOT NULL,
        Obra varchar(100) NOT NULL,
        Partida varchar(120) NOT NULL,
        Metrado decimal(10,2) NOT NULL,
        Tarifa decimal(10,2) NOT NULL,
        Total decimal(12,2) NOT NULL,
        Observacion varchar(250) NULL,
        FechaRegistro datetime NOT NULL CONSTRAINT DF_RRHH_Destajo_FechaRegistro DEFAULT (GETDATE()),
        CONSTRAINT PK_RRHH_Destajo PRIMARY KEY CLUSTERED (IDdestajo ASC),
        CONSTRAINT FK_RRHH_Destajo_Empleado FOREIGN KEY (IDempleado) REFERENCES dbo.Empleado(IDempleado),
        CONSTRAINT FK_RRHH_Destajo_Contrato FOREIGN KEY (IDcontrato) REFERENCES dbo.RRHH_Contrato(IDcontrato),
        CONSTRAINT CK_RRHH_Destajo_Metrado CHECK (Metrado > 0),
        CONSTRAINT CK_RRHH_Destajo_Tarifa CHECK (Tarifa >= 0),
        CONSTRAINT CK_RRHH_Destajo_Total CHECK (Total >= 0)
    );
END
GO

IF OBJECT_ID('dbo.RRHH_Auditoria', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RRHH_Auditoria (
        IDaudit int IDENTITY(1,1) NOT NULL,
        Modulo varchar(40) NOT NULL,
        Accion varchar(40) NOT NULL,
        Entidad varchar(40) NOT NULL,
        EntidadID int NULL,
        Descripcion varchar(300) NOT NULL,
        Payload nvarchar(max) NULL,
        Fecha datetime NOT NULL CONSTRAINT DF_RRHH_Auditoria_Fecha DEFAULT (GETDATE()),
        Usuario varchar(80) NOT NULL CONSTRAINT DF_RRHH_Auditoria_Usuario DEFAULT (SUSER_SNAME()),
        CONSTRAINT PK_RRHH_Auditoria PRIMARY KEY CLUSTERED (IDaudit ASC)
    );
END
GO

CREATE OR ALTER VIEW dbo.Vista_RRHH_Contratos_Alertas
AS
SELECT
    c.IDcontrato,
    c.CodigoContrato,
    c.IDempleado,
    e.NumeroDocumento,
    CONCAT(e.Nombres, ' ', e.ApellidoPaterno, ' ', e.ApellidoMaterno) AS Empleado,
    ISNULL(NULLIF(det.Area, ''), 'Sin area') AS Area,
    c.Obra,
    c.Cargo,
    c.FechaInicio,
    c.FechaFin,
    c.SalarioDiario,
    c.Estado,
    c.FechaLiquidacion,
    c.TotalLiquidacion,
    DATEDIFF(DAY, CAST(GETDATE() AS date), c.FechaFin) AS DiasRestantes,
    CASE
        WHEN c.Estado = 'liquidado' THEN 'gris'
        WHEN c.FechaFin < CAST(GETDATE() AS date) THEN 'rojo'
        WHEN DATEDIFF(DAY, CAST(GETDATE() AS date), c.FechaFin) <= 7 THEN 'rojo'
        WHEN DATEDIFF(DAY, CAST(GETDATE() AS date), c.FechaFin) <= 30 THEN 'amarillo'
        ELSE 'verde'
    END AS Semaforo
FROM dbo.RRHH_Contrato c
JOIN dbo.Empleado e ON c.IDempleado = e.IDempleado
OUTER APPLY (
    SELECT TOP 1 Area
    FROM dbo.Detalle_Empleado de
    WHERE de.IDempleado = e.IDempleado
    ORDER BY de.IDdetalleEmpleado DESC
) det;
GO

CREATE OR ALTER VIEW dbo.Vista_RRHH_Planilla_Resumen
AS
WITH asistencia AS (
    SELECT
        a.IDempleado,
        a.Obra,
        CAST(a.Fecha AS date) AS Fecha,
        SUM(CASE WHEN a.Estado IN ('presente', 'tardanza') THEN a.Horas ELSE 0 END) AS HorasLaboradas,
        SUM(a.Extras) AS Extras
    FROM dbo.RRHH_Asistencia a
    GROUP BY a.IDempleado, a.Obra, CAST(a.Fecha AS date)
),
destajo AS (
    SELECT
        d.IDempleado,
        d.Obra,
        CAST(d.Fecha AS date) AS Fecha,
        SUM(d.Total) AS TotalDestajo
    FROM dbo.RRHH_Destajo d
    GROUP BY d.IDempleado, d.Obra, CAST(d.Fecha AS date)
)
SELECT
    COALESCE(a.IDempleado, d.IDempleado) AS IDempleado,
    e.NumeroDocumento,
    CONCAT(e.Nombres, ' ', e.ApellidoPaterno, ' ', e.ApellidoMaterno) AS Empleado,
    ISNULL(NULLIF(det.Area, ''), 'Sin area') AS Area,
    COALESCE(a.Obra, d.Obra) AS Obra,
    COALESCE(a.Fecha, d.Fecha) AS Fecha,
    ISNULL(a.HorasLaboradas, 0) AS HorasLaboradas,
    ISNULL(a.Extras, 0) AS Extras,
    ISNULL(d.TotalDestajo, 0) AS TotalDestajo,
    ISNULL(c.SalarioDiario, 0) AS SalarioDiario,
    CAST((ISNULL(a.HorasLaboradas, 0) / 8.0) * ISNULL(c.SalarioDiario, 0) AS decimal(12,2)) AS Jornal,
    CAST(((ISNULL(a.HorasLaboradas, 0) / 8.0) * ISNULL(c.SalarioDiario, 0)) + ISNULL(a.Extras, 0) + ISNULL(d.TotalDestajo, 0) AS decimal(12,2)) AS TotalPlanilla
FROM asistencia a
FULL OUTER JOIN destajo d
    ON a.IDempleado = d.IDempleado
   AND a.Obra = d.Obra
   AND a.Fecha = d.Fecha
JOIN dbo.Empleado e ON e.IDempleado = COALESCE(a.IDempleado, d.IDempleado)
OUTER APPLY (
    SELECT TOP 1 Area
    FROM dbo.Detalle_Empleado de
    WHERE de.IDempleado = e.IDempleado
    ORDER BY de.IDdetalleEmpleado DESC
) det
OUTER APPLY (
    SELECT TOP 1 SalarioDiario
    FROM dbo.RRHH_Contrato c
    WHERE c.IDempleado = COALESCE(a.IDempleado, d.IDempleado)
      AND c.Obra = COALESCE(a.Obra, d.Obra)
      AND c.Estado <> 'liquidado'
    ORDER BY c.FechaInicio DESC
) c;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Documento WHERE TipoDocumento = 'DNI')
BEGIN
    INSERT INTO dbo.Tipo_Documento (TipoDocumento) VALUES ('DNI');
END
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Documento WHERE TipoDocumento = 'Carnet de extranjeria')
BEGIN
    INSERT INTO dbo.Tipo_Documento (TipoDocumento) VALUES ('Carnet de extranjeria');
END
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Documento WHERE TipoDocumento = 'RUC')
BEGIN
    INSERT INTO dbo.Tipo_Documento (TipoDocumento) VALUES ('RUC');
END
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Empleado WHERE TipoEmpleado = 'Operario')
BEGIN
    INSERT INTO dbo.Tipo_Empleado (TipoEmpleado) VALUES ('Operario');
END
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Empleado WHERE TipoEmpleado = 'Administrativo')
BEGIN
    INSERT INTO dbo.Tipo_Empleado (TipoEmpleado) VALUES ('Administrativo');
END
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Empleado WHERE TipoEmpleado = 'Supervisor')
BEGIN
    INSERT INTO dbo.Tipo_Empleado (TipoEmpleado) VALUES ('Supervisor');
END
GO
