# -----------------Proposed algorithm------------
# Step 1: Find the best fit for the NF instances --> This is familiarity, resulting in a set of NS candidates
# Step 2: The constraint regarding the NF instances -> This results in only one NS

import uuid


def meso_algorithm(nf_set, system_sfc_dict, req_sfc, min_reuse):
    default_dict = system_sfc_dict
    # Detemine the number of NFs
    req_lenSFC = len(req_sfc)
    req_sumNFins = 0
    # Determine the number of NF instances
    for nf_index, nf_instances in req_sfc.items():
        req_sumNFins = req_sumNFins + nf_instances
    # Step 1
    is_matched = 0
    sfc_candidates = dict()
    sfc_reserve = dict()
    extraNFins = 0
    if len(system_sfc_dict) == 0:
        sfc_id = uuid.uuid4()
        system_sfc_dict[sfc_id] = dict()
        for req_nf_index, req_nf_instances in req_sfc.items():
            for nf_index, nf_cp in nf_set.items():
                if nf_index == req_nf_index:
                    avail_ins = nf_cp - 1
                    nf_instances_dict = dict()
                    system_sfc_dict[sfc_id][nf_index] = dict()
                    for nf_instance_index in range(0, req_nf_instances):
                        nf_instance_id = uuid.uuid4()
                        nf_instances_dict[nf_instance_id] = avail_ins
                    system_sfc_dict[sfc_id][nf_index].update(nf_instances_dict)
        extraNFins = req_sumNFins
        return extraNFins, is_matched
    for sfc_id, sfc_render in system_sfc_dict.items():
        sfc_candidates[sfc_id] = list()
        sfc_reserve[sfc_id] = dict()
        for nf_index, nf_instances_dict in sfc_render.items():
            numNFins = len(
                [nf_instance_index for nf_instance_index, avail_nfins in nf_instances_dict.items() if avail_nfins > 0])
            for i, j in req_sfc.items():
                if (nf_index == i):
                    if (numNFins >= j):
                        sfc_candidates[sfc_id].append(nf_index)
                        sfc_reserve[sfc_id].update({i: j})
                    else:
                        sfc_reserve[sfc_id].update({i: numNFins})

    # if len([sfc_index for sfc_index, fam_list in sfc_candidates.items() if len(fam_list)!=0]) != 0:
    #    return off_sfcs  # The worst case

    sfc_list = list()
    for sfc_id, fam_list in sfc_candidates.items():
        if len(fam_list) == req_lenSFC:
            sfc_list.append(sfc_id)
            is_matched = 1
            # This results in the set of SFC candidates: sfc_list

            # -------------------------------------------------------------
            # Step 2: Choose the best-fit one which is satisfied with both NFs and NF instances
            # sumreqSFC = 0
            # for nf_index, nf_instances in req_sfc.items():
            #  sumreqSFC = sumreqSFC + nf_instances
    if is_matched:
        sumSFC_dict = dict()
        for i in sfc_list:
            for sfc_index, sfc_render in system_sfc_dict.items():
                if sfc_index == i:
                    sumSFC_dict[i] = 0
                    for nf_index, nf_instances_dict in sfc_render.items():
                        nf_instances = sum(
                            [avail_nfins for nfins_index, avail_nfins in nf_instances_dict.items() if avail_nfins > 0])
                        sumSFC_dict[i] = sumSFC_dict[i] + nf_instances

                        # for sfc_index, sum_sfc in sumSFC_dict.items():
                        #   eff_factor[sfc_index] = sumreqSFC/sum_sfc
        selected_sfc = min(sumSFC_dict, key=sumSFC_dict.get)
        # Determine sfc resource reservation - Round-robin scheduling
        # Update avail_nfins
        if selected_sfc:
            for sfc_id, render_sfc in system_sfc_dict.items():
                if sfc_id == selected_sfc:
                    for sys_nf_index, sys_nf_instances_dict in render_sfc.items():
                        for req_nf_index, req_nf_instances in req_sfc.items():
                            if req_nf_index == sys_nf_index:
                                for nfins_index, avail_nfins in sys_nf_instances_dict.items():
                                    if (avail_nfins > 0) & (req_nf_instances > 0):
                                        # avail_nfins = avail_nfins - 1
                                        sys_nf_instances_dict[nfins_index] = sys_nf_instances_dict[nfins_index] - 1
                                        req_nf_instances = req_nf_instances - 1

                                        # -------------------------------------------------------------
                                        # Step 3: Choose the best-fit one which is satisfied with only NFs
    else:
        sfc_filter = dict()
        for sfc_id, nf_dict in sfc_reserve.items():
            if len(nf_dict) == req_lenSFC:
                sfc_filter[sfc_id] = 0
                for nf_index, nf_instances in nf_dict.items():
                    sfc_filter[sfc_id] = sfc_filter[sfc_id] + nf_instances

        sfc_set = dict()
        for sfc_index, total_nfs in sfc_filter.items():
            coff = total_nfs / float(req_sumNFins)
            if coff >= min_reuse:
                sfc_set[sfc_index] = coff
        if not sfc_set:
            system_sfc_dict = default_dict
            sfc_id = uuid.uuid4()
            system_sfc_dict[sfc_id] = dict()
            for req_nf_index, req_nf_instances in req_sfc.items():
                for nf_index, nf_cp in nf_set.items():
                    if nf_index == req_nf_index:
                        avail_ins = nf_cp - 1
                        nf_instances_dict = dict()
                        system_sfc_dict[sfc_id][nf_index] = dict()
                        for nf_instance_index in range(0, req_nf_instances):
                            nf_instance_id = uuid.uuid4()
                            nf_instances_dict[nf_instance_id] = avail_ins
                        system_sfc_dict[sfc_id][nf_index].update(nf_instances_dict)
            extraNFins = req_sumNFins
            return extraNFins, is_matched
        selected_sfc = max(sfc_set, key=sfc_set.get)
        is_matched = 1

        # Determine sfc resources
        extraNFins = 0
        if selected_sfc:
            for sfc_index, render_sfc in system_sfc_dict.items():
                if sfc_index == selected_sfc:
                    for sys_nf_index, sys_nf_instances_dict in render_sfc.items():
                        for req_nf_index, req_nf_instances in req_sfc.items():
                            if req_nf_index == sys_nf_index:
                                # nf_instances = sum([avail_nfins for nfins_index, avail_nfins in sys_nf_instances_dict.items() if avail_nfins > 0])
                                # Round - robin scheduling
                                for nfins_index, avail_nfins in sys_nf_instances_dict.items():
                                    if (avail_nfins > 0) & (req_nf_instances > 0):
                                        # avail_nfins = avail_nfins - 1
                                        sys_nf_instances_dict[nfins_index] = sys_nf_instances_dict[nfins_index] - 1
                                        req_nf_instances = req_nf_instances - 1
                                if req_nf_instances > 0:
                                    extraNFins = req_nf_instances
                                    for nf_index, nf_cp in nf_set.items():
                                        if nf_index == req_nf_index:
                                            avail_ins = nf_cp - 1
                                            for i in range(0, extraNFins):
                                                nf_instance_id = uuid.uuid4()
                                                sys_nf_instances_dict.update({nf_instance_id: avail_ins})
    if not is_matched:
        system_sfc_dict = default_dict
        sfc_id = uuid.uuid4()
        system_sfc_dict[sfc_id] = dict()
        for req_nf_index, req_nf_instances in req_sfc.items():
            for nf_index, nf_cp in nf_set.items():
                if nf_index == req_nf_index:
                    avail_ins = nf_cp - 1
                    nf_instances_dict = dict()
                    system_sfc_dict[sfc_id][nf_index] = dict()
                    for nf_instance_index in range(0, req_nf_instances):
                        nf_instance_id = uuid.uuid4()
                        nf_instances_dict[nf_instance_id] = avail_ins
                    system_sfc_dict[sfc_id][nf_index].update(nf_instances_dict)
        extraNFins = req_sumNFins
    return extraNFins, is_matched

    # Determine the reuse factor is matched
    # Return number of VMs that are used
    # Return the list of offerred NSs that is reused
    # Return the number of requested NSs that reused the existing the NS. It is a dict, if no NFs are needed, {NS1:0}, but if have, {NS1: {NF1:2}}
    # Set the dict: A = {req_NS1: {off_NS5:{NF1:2, NF3:1}}}
    # Return the rest resources: I mean off_sfcs

    # Value returned cannot be negative