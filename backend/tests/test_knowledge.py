import unittest
from datetime import datetime, timezone
import test_api as support
from app.knowledge import literal_pattern


class PatternTest(unittest.TestCase):
    def test_sql_wildcards_are_literal(self):
        self.assertEqual(literal_pattern("100%_"),"%100\\%\\_%")


class KnowledgeTest(support.Fixture):
    def test_unapproved_and_other_factory_excluded(self):
        item=self.create()
        self.assertEqual(self.client.get("/knowledge?q=공구",headers=self.worker).json()["sources"],[])
        self.client.post(f"/incidents/{item}/actions",headers=self.worker,json={"action":"공구 교체","outcome":"정상"})
        self.client.post(f"/incidents/{item}/approve",headers=self.supervisor,
                         json={"resolved":True,"evidence":"재가동 확인","ended_at":datetime.now(timezone.utc).isoformat()})
        result=self.client.get("/knowledge?q=공구",headers=self.worker).json()
        self.assertEqual(result["sources"][0]["citation"],"/incidents/"+item)
        for outsider in [self.other,self.other_factory]:
            self.assertEqual(self.client.get("/knowledge?q=공구",headers=outsider).json()["sources"],[])
