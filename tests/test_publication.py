"""Comprueba exclusiones sin crear un repositorio Git en el proyecto."""
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PublicationTests(unittest.TestCase):
    def test_generated_files_and_credentials_are_ignored(self):
        private=['.env','.env.production','.secrets/access.txt','.secrets/operator.htpasswd','deploy/lxc/access.txt','bronze.gz','deploy/lxc/demo-handoff.tgz','data/bronze/test.parquet','.claude/settings.json','services/webapp/node_modules/a.js','services/webapp/dist/index.html','services/api/app/__pycache__/a.pyc','dbt/target/manifest.json','dbt/.user.yml','compose.server.json']
        public=['.env.example','docker-compose.yml','deploy/lxc/compose.yml','services/webapp/package-lock.json','services/api/app/inferencia.py','scripts/prepare_map.py','tests/test_setup.py']
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git','init','-q',tmp],check=True)
            r=subprocess.run(['git',f'--git-dir={tmp}/.git',f'--work-tree={ROOT}','check-ignore','--no-index','--stdin'],input='\n'.join(private+public)+'\n',text=True,capture_output=True,cwd=ROOT)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(set(r.stdout.splitlines()),set(private))
if __name__=='__main__':unittest.main()
