"""Read-only gateway reference for industrial PC. No register-write methods."""
import argparse
import json
import os
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from uuid import uuid4


class Outbox:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, payload TEXT NOT NULL, error TEXT)")

    def add(self, payload):
        encoded = json.dumps(payload, sort_keys=True)
        previous = self.db.execute("SELECT payload FROM outbox WHERE id=?", (payload["event_id"],)).fetchone()
        if previous and previous[0] != encoded:
            raise ValueError("event ID conflict")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO outbox(id,payload) VALUES (?,?)",(payload["event_id"],encoded))

    def flush(self, send):
        for key, payload in self.db.execute("SELECT id,payload FROM outbox WHERE error IS NULL ORDER BY rowid").fetchall():
            try:
                send(json.loads(payload))
            except urllib.error.HTTPError as exc:
                if exc.code in (400,403,404,409,422):
                    with self.db:
                        self.db.execute("UPDATE outbox SET error=? WHERE id=?",(str(exc.code),key))
                    continue
                break
            except (OSError, TimeoutError):
                break
            with self.db:
                self.db.execute("DELETE FROM outbox WHERE id=?",(key,))


def read_register(client, address, slave, scale):
    response = client.read_input_registers(address, count=1, slave=slave)
    if response.isError() or len(response.registers) != 1:
        raise ValueError("invalid Modbus reading")
    return response.registers[0] * scale


def sample(sensor, value, source):
    return dict(sensor_id=sensor,event_id=str(uuid4()),observed_at=datetime.now(timezone.utc).isoformat(),
                metric="power_kw",value=value,unit="kW",quality="estimated" if source=="simulator" else "good",
                source=source,firmware_version="gateway-reference-0.1")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--sensor",required=True)
    parser.add_argument("--outbox",default="outbox.sqlite3")
    parser.add_argument("--transport",choices=["simulator","tcp","rtu"],default="simulator")
    parser.add_argument("--host")
    parser.add_argument("--serial-port")
    parser.add_argument("--port",type=int,default=502)
    parser.add_argument("--baudrate",type=int,default=9600)
    parser.add_argument("--slave",type=int,default=1)
    parser.add_argument("--address",type=int,default=0)
    parser.add_argument("--scale",type=float,default=1)
    parser.add_argument("--once",action="store_true")
    args=parser.parse_args()
    url=os.environ["INGEST_URL"]
    if not url.startswith("https://") and not url.startswith("http://localhost:"):
        raise SystemExit("Use HTTPS for non-local ingestion")
    token=os.environ["DEVICE_TOKEN"]
    def send(payload):
        req=urllib.request.Request(url,data=json.dumps(payload).encode(),method="POST",
            headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=10) as response:
            if response.status != 201:
                raise OSError("ingestion not acknowledged")
    client=None
    if args.transport!="simulator":
        from pymodbus.client import ModbusTcpClient, ModbusSerialClient
        client=(ModbusTcpClient(args.host,port=args.port,timeout=3) if args.transport=="tcp"
                else ModbusSerialClient(args.serial_port,baudrate=args.baudrate,timeout=3))
        if not client.connect():
            raise SystemExit("Modbus connection unavailable")
    outbox=Outbox(args.outbox)
    try:
        while True:
            outbox.flush(send)
            try:
                value=read_register(client,args.address,args.slave,args.scale) if client else 12.5
                outbox.add(sample(args.sensor,value,"modbus_"+args.transport if client else "simulator"))
                outbox.flush(send)
            except ValueError:
                print("Meter read failed; no fabricated measurement stored",flush=True)
            if args.once: break
            time.sleep(10)
    finally:
        if client: client.close()
        outbox.db.close()


if __name__=="__main__":
    main()
