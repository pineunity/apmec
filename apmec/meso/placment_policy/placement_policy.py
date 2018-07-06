# -----------------Proposed algorithm------------
# Step 1: Find the best fit for the NF instances --> This is familiarity, resulting in a set of NS candidates
# Step 2: The constraint regarding the NF instances -> This results in only one NS

import uuid


def meso_algorithm(sys_nf_list, system_sfc_dict, req_sfc, min_reuse):
