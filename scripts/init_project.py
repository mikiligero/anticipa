"""Genera secretos locales una sola vez; nunca sustituye credenciales existentes."""
from pathlib import Path
import argparse
import secrets
import subprocess


def initialize(root: Path):
    env = root / '.env'
    private = root / '.secrets'
    private.mkdir(mode=0o700, exist_ok=True)
    if not env.exists():
        content = (root / '.env.example').read_text()
        content = content.replace('API_TOKEN=\n', f'API_TOKEN={secrets.token_hex(24)}\n')
        env.write_text(content)
        env.chmod(0o600)
    auth = private / 'operator.htpasswd'
    if not auth.exists():
        password = secrets.token_urlsafe(20)
        hashed = subprocess.run(['openssl','passwd','-apr1','-stdin'], input=password, text=True, capture_output=True,check=True).stdout.strip()
        config = dict(line.split('=',1) for line in env.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
        username = config.get('OPERATOR_USER','operador')
        if not username or any(c in username for c in ':\r\n'):
            raise ValueError('OPERATOR_USER no válido')
        auth.write_text(f'{username}:{hashed}\n')
        auth.chmod(0o644)  # nginx debe poder leer el hash dentro del contenedor.
        access = private / 'access.txt'
        access.write_text(f'Usuario: {username}\nClave: {password}\n')
        access.chmod(0o600)
    print('Configuración preparada. Credenciales privadas: .secrets/access.txt')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    initialize(parser.parse_args().root)
