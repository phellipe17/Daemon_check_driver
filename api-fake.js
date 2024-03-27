const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3000;

// Middleware para analisar corpos de solicitações JSON
app.use(bodyParser.json());

// Rota para lidar com o heartbeat
app.post('/heartbeat', (req, res) => {
  const receivedObject = req.body; // Objeto recebido na solicitação POST
  console.log('Objeto recebido:', receivedObject);
  res.send('Objeto recebido com sucesso!');
});

// Iniciar o servidor
app.listen(PORT, () => {
  console.log(`Servidor ouvindo na porta ${PORT}`);
});
