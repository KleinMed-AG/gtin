export default function handler(req, res) {
  const basicAuth = req.headers.authorization;

  // Define your credentials
  const validUsername = os.getenv("USERNAME");
  const validPassword = os.getenv("PASSWORD")

  if (basicAuth) {
    const authValue = basicAuth.split(' ')[1];
    const [user, pwd] = Buffer.from(authValue, 'base64').toString().split(':');

    if (user === validUsername && pwd === validPassword) {
      return res.status(200).json({ authenticated: true });
    }
  }

  // Send 401 with WWW-Authenticate header
  res.setHeader('WWW-Authenticate', 'Basic realm="Secure Area"');
  return res.status(401).json({ authenticated: false });
}
