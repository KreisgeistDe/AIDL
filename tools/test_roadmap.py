from __future__ import annotations
import json, shutil, tempfile, unittest
from pathlib import Path
from tools import roadmap

ROOT=Path(__file__).resolve().parents[1]

class RoadmapTest(unittest.TestCase):
    def temp_repo(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        shutil.copytree(ROOT/"roadmap",root/"roadmap")
        (root/"spec").mkdir(); shutil.copy2(ROOT/"spec/roadmap-v1.schema.json",root/"spec/roadmap-v1.schema.json")
        shutil.copytree(ROOT/"backlog",root/"backlog")
        shutil.copy2(ROOT/"TODO.md",root/"TODO.md")
        return td,root

    def write(self,root,path,data):
        (root/path).write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")

    def test_complete_repository_and_current_ready_work(self):
        self.assertEqual([],roadmap.validate_repository(ROOT))
        summary=roadmap.summary_data(ROOT)
        self.assertEqual(26,summary["milestones"])
        self.assertEqual([],summary["pending_migration"])
        self.assertEqual("M10.5-04",roadmap.next_data(ROOT)["next"]["id"])
        self.assertEqual(["M10.5-06"],[x["id"] for x in roadmap.blockers_data("M11-04.1",ROOT)["blockers"]])
        completed={x["id"] for x in roadmap.completed_data(ROOT)["completed"]}
        self.assertIn("M9-06",completed);self.assertIn("M9-08",completed)

    def test_context_is_bounded_and_deterministic(self):
        a=roadmap.context_data(ROOT,limit=3);b=roadmap.context_data(ROOT,limit=3)
        self.assertEqual(a,b);self.assertEqual(3,len(a["items"]));self.assertTrue(a["truncated"])
        self.assertEqual("M10.5-04",a["next"]["id"])

    def test_ids_cover_dotted_and_experiment_forms(self):
        _,_,packages,_=roadmap.load_authority(ROOT)
        self.assertIn("M11-04.1",packages);self.assertIn("M11.5",packages);self.assertIn("M16.5-E9",packages)

    def test_unknown_self_and_dependency_cycle_fail(self):
        for mode,code in (("unknown","ROADMAP-E003"),("self","ROADMAP-E004"),("cycle","ROADMAP-E005")):
            td,root=self.temp_repo()
            try:
                p=Path("roadmap/v1/milestones/m10.5.json");d=json.loads((root/p).read_text())
                if mode=="unknown":d["packages"][3]["depends_on"]=["M404-01"]
                elif mode=="self":d["packages"][3]["depends_on"]=["M10.5-04"]
                else:
                    d["packages"][2]["depends_on"]=["M10.5-04"];d["packages"][3]["depends_on"]=["M10.5-03"]
                self.write(root,p,d)
                self.assertIn(code,{e["code"] for e in roadmap.validate_repository(root,check_markdown=False)})
            finally:td.cleanup()

    def test_duplicate_ids_and_orders_fail(self):
        td,root=self.temp_repo()
        try:
            p=Path("roadmap/v1/milestones/m10.5.json");d=json.loads((root/p).read_text())
            d["packages"][1]["id"]=d["packages"][0]["id"];d["packages"][2]["order"]=d["packages"][1]["order"];self.write(root,p,d)
            self.assertIn("ROADMAP-E002",{e["code"] for e in roadmap.validate_repository(root,check_markdown=False)})
        finally:td.cleanup()

    def test_supersession_valid_and_invalid_cases(self):
        td,root=self.temp_repo()
        try:
            p=Path("roadmap/v1/milestones/m10.5.json");d=json.loads((root/p).read_text())
            old,new=d["packages"][4],d["packages"][5]
            old["status"]="superseded";old["disposition_reason"]="replaced by later accepted package";old["superseded_by"]=[new["id"]];new["supersedes"]=[old["id"]]
            self.write(root,p,d)
            self.assertEqual([],roadmap.validate_repository(root,check_markdown=False))
            view=roadmap.superseded_data(root);self.assertEqual("M10.5-05",view["packages"][0]["id"])
            new["supersedes"]=["M404-01"];self.write(root,p,d)
            self.assertIn("ROADMAP-E010",{e["code"] for e in roadmap.validate_repository(root,check_markdown=False)})
        finally:td.cleanup()

    def test_supersession_reciprocity_and_cycle_fail(self):
        td,root=self.temp_repo()
        try:
            p=Path("roadmap/v1/milestones/m10.5.json");d=json.loads((root/p).read_text())
            a,b=d["packages"][4],d["packages"][5]
            a["status"]="superseded";a["disposition_reason"]="historical";a["superseded_by"]=[b["id"]]
            self.write(root,p,d)
            self.assertIn("ROADMAP-E011",{e["code"] for e in roadmap.validate_repository(root,check_markdown=False)})
            b["supersedes"]=[a["id"]];b["superseded_by"]=[a["id"]];a["supersedes"]=[b["id"]]
            self.write(root,p,d)
            self.assertIn("ROADMAP-E012",{e["code"] for e in roadmap.validate_repository(root,check_markdown=False)})
        finally:td.cleanup()

    def test_projection_drift_fails(self):
        td,root=self.temp_repo()
        try:
            p=root/"backlog/m17-m21-full-language-coverage.md";text=p.read_text();text=text.replace("- [ ] **P1**","- [x] **P1**",1);p.write_text(text)
            self.assertIn("ROADMAP-E008",{e["code"] for e in roadmap.validate_repository(root)})
        finally:td.cleanup()

    def test_index_migration_partition_and_link_validation_fail_closed(self):
        td,root=self.temp_repo()
        try:
            ip=Path("roadmap/v1/index.json");idx=json.loads((root/ip).read_text());idx["migration"]["pending_milestones"]=["M21"];self.write(root,ip,idx)
            self.assertIn("ROADMAP-E009",{e["code"] for e in roadmap.validate_repository(root,check_markdown=False)})
        finally:td.cleanup()
        td,root=self.temp_repo()
        try:
            p=Path("roadmap/v1/milestones/m10.5.json");d=json.loads((root/p).read_text());d["packages"][0]["evidence"]=[{"kind":"path","ref":"missing.md"}];self.write(root,p,d)
            self.assertIn("ROADMAP-E006",{e["code"] for e in roadmap.validate_repository(root,check_markdown=False)})
        finally:td.cleanup()

if __name__=="__main__":unittest.main()
