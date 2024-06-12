///REQUIRED INSTALL npm install express multer
const app = express();
const PORT = 5000;

const express = require('express');
const multer = require('multer');
const path = require('path');
const os = require('os');

// Função para construir o caminho dinâmico para o diretório Documents
const getDocumentsPath = () => {
    return path.join(os.homedir(), 'Documents');
};

// Configuração do Multer para salvar arquivos no diretório Documents dinamicamente
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const documentsPath = getDocumentsPath();
        cb(null, documentsPath);
    },
    filename: (req, file, cb) => {
        cb(null, file.originalname);
    }
});

const upload = multer({ storage: storage });

// Rota para receber o upload de arquivos
app.post('/heartbeat', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    console.log(`Received message: ${req.body}`);

    // O arquivo foi salvo com sucesso
    res.status(200).json({
        message: 'File successfully uploaded',
        filePath: req.file.path
    });
});

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});