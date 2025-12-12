from acl_anthology import Anthology
import json

anth = Anthology.from_repo(verbose=True)
paper = anth.get_paper("2020.acl-main.1")
# Get references (IDs of papers this one cites)
print(json.dumps(paper.citeproc_dict, indent=4))
