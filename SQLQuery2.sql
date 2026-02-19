-- 1. Tabela de Notícias (Histórico + Scraper)
CREATE TABLE Noticias (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Titulo NVARCHAR(MAX),
    Descricao NVARCHAR(MAX),
    Link NVARCHAR(450) UNIQUE, -- Unique para evitar duplicados
    DataPublicacao DATETIME,
    Fonte NVARCHAR(100),
    Categoria NVARCHAR(100),
    N_Palavras_Titulo INT,
    N_Palavras_Desc INT,
    Dia_Semana INT,
    Hora INT,
    Sentimento INT,
    DataInsercao DATETIME DEFAULT GETDATE()
);
GO

-- 2. Tabela de Feedback (Human-in-the-Loop)
CREATE TABLE Feedback (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Titulo_Input NVARCHAR(MAX),
    Descricao_Input NVARCHAR(MAX),
    Categoria_Input NVARCHAR(100),
    N_Palavras_Titulo INT,
    N_Palavras_Desc INT,
    Sentimento INT,
    Dia_Semana INT,
    Hora INT,
    Popularidade_Real NVARCHAR(50),
    DataFeedback DATETIME DEFAULT GETDATE()
);
GO