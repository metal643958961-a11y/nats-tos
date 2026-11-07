"""Validate and build one deterministic TOS Docker archive. Requires Python 3 and Ruby/Psych."""
import configparser
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "package"
APP = "nats"
FILES = sorted(("config.ini", APP + ".lang", APP + ".svg", "docker-compose.yml"))
IMAGE = "nats:2.15.2-scratch@sha256:6157c118e1f123b1d7ee3bc74906b2f52611d95fe1679e921f032a0fe38a129b"


def check(ok, label):
    if not ok:
        raise ValueError(label)


def build():
    check(sorted(p.name for p in SRC.iterdir()) == FILES, "unexpected package files")
    check(all((SRC/f).is_file() and not (SRC/f).is_symlink() for f in FILES), "regular files only")
    c = json.loads((SRC/"config.ini").read_text())
    y = json.loads(subprocess.check_output(["ruby", "-ryaml", "-rjson", "-e",
        "puts JSON.generate(YAML.safe_load(File.read(ARGV.fetch(0))))", str(SRC/"docker-compose.yml")]))
    service = y["services"][APP]
    check(c["id"] == c["compose_project"] == service["container_name"] == APP, "application identity")
    check(c["application_type"] == "docker" and c["platform"] == "x86_64" and
          c["depend"] == ["DockerEngine"] and c["version"] == "2.15.2.1", "architecture and version")
    check(service["image"] == IMAGE and service["platform"] == "linux/amd64", "image pin")
    check(not c["open_path"] and "x-app-meta" not in y and service["ports"] == ["127.0.0.1:14222:4222"], "headless local service")
    check(service["user"] == c["user"] == "1000:1000" and service["read_only"] and service["cap_drop"] == ["ALL"] and service["security_opt"] == ["no-new-privileges:true"], "permissions")
    check(service["volumes"] == ["./data:/data"], "mounts")
    lang = configparser.ConfigParser()
    lang.read(SRC/(APP+".lang"), encoding="utf-8")
    check(len(lang.sections()) == 26 and all(json.loads(lang[s][k]).strip() for s in lang for k in
          ("name","auth","descript") if s != "DEFAULT"), "languages")
    check(c["icon"] == f"/images/icons/{APP}.svg" and ElementTree.parse(SRC/(APP+".svg")).getroot().tag ==
          "{http://www.w3.org/2000/svg}svg", "icon")
    check("Apache License" in (ROOT/"licenses/NATS-Apache-2.0.txt").read_text(), "upstream notice")
    archive = io.BytesIO()
    with gzip.GzipFile(fileobj=archive, mode="wb", mtime=0) as gz, tarfile.open(fileobj=gz,mode="w") as tar:
        for f in FILES:
            raw = (SRC/f).read_bytes()
            info = tarfile.TarInfo(f)
            info.mode, info.size = 0o644, len(raw)
            tar.addfile(info, io.BytesIO(raw))
    payload = archive.getvalue()
    with tarfile.open(fileobj=io.BytesIO(payload)) as tar:
        check(tar.getnames() == FILES and all(tar.extractfile(f).read() == (SRC/f).read_bytes() for f in FILES), "archive round trip")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/"dist"
    out.mkdir(parents=True,exist_ok=True)
    name = APP + ".tar.gz"
    (out/name).write_bytes(payload)
    line = hashlib.sha256(payload).hexdigest() + "  " + name
    (out/"SHA256SUMS").write_text(line+"\n")
    print(line)


if __name__ == "__main__":
    build()
