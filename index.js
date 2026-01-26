const fs = require('fs');
const path = require('path');

module.exports = (req, res) => {
  const indexPath = path.join(__dirname, 'index.html');
  const indexHtml = fs.readFileSync(indexPath, 'utf8');
  
  res.setHeader('Content-Type', 'text/html');
  res.status(200).send(indexHtml);
};
