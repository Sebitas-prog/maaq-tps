USE maaq_bd;
GO

IF EXISTS (
    SELECT 1
    FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Cliente')
      AND name = 'Email'
)
BEGIN
    ALTER TABLE dbo.Cliente ALTER COLUMN Email varchar(100) NULL;
END
GO
