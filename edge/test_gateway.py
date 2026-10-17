import tempfile
import unittest
from pathlib import Path
from gateway import Outbox, read_register, sample


class GatewayTest(unittest.TestCase):
    def test_restart_retry(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/"outbox.db")
            q=Outbox(path); payload=sample("sensor",1,"simulator");q.add(payload)
            def offline(_): raise OSError("offline")
            q.flush(offline);q.db.close()
            q=Outbox(path);sent=[];q.flush(sent.append)
            self.assertEqual(sent,[payload])
            q.flush(sent.append);self.assertEqual(len(sent),1)
            q.db.close()

    def test_conflicting_key(self):
        q=Outbox(":memory:");p=sample("sensor",1,"simulator");q.add(p)
        with self.assertRaises(ValueError):q.add({**p,"value":2})
        q.db.close()

    def test_read_only_adapter(self):
        class Response:
            registers=[123]
            def isError(self):return False
        class Client:
            def read_input_registers(self,address,count,slave):
                self.request=(address,count,slave);return Response()
        c=Client();self.assertAlmostEqual(read_register(c,10,1,.1),12.3)
        self.assertEqual(c.request,(10,1,1))

    def test_simulation_is_estimated(self):
        self.assertEqual(sample("sensor",1,"simulator")["quality"],"estimated")
