import pickle
import matplotlib.pyplot as plt
# import cPickle as pickle
from matplotlib import legend_handler
import numpy as np
from confidence import mean_confidence_interval

path = "/home/test/00-OpenStack-repo/00-apmec-server/wallaby/apmec/samples/tosca-templates/evaluation/papers/"

# =======================================================================================
sap_total_cost_result_dict = pickle.load(open(path + "sap_total_cost_results.pickle", "rb"))
sap_total_comp_result_dict = pickle.load(open(path + "sap_comp_cost_results.pickle", "rb"))
sap_total_config_cost_result_dict = pickle.load(open(path + "sap_config_cost_results.pickle", "rb"))
sap_req_result_dict = pickle.load(open(path + "sap_req_results.pickle", "rb"))


print sap_total_cost_result_dict, len(sap_total_cost_result_dict)

sap_total_cost_result = list()
sap_total_cost_err = list()

for num in sap_total_cost_result_dict:
    result, err = mean_confidence_interval(sap_total_cost_result_dict[num], confidence=0.95)
    sap_total_cost_result.append(result)
    sap_total_cost_err.append(err)

sap_total_requests_result = list()
sap_total_requests_err = list()

for num in sap_req_result_dict:
    result, err = mean_confidence_interval(sap_req_result_dict[num], confidence=0.95)
    sap_total_requests_result.append(result)
    sap_total_requests_err.append(err)

sap_total_comp_cost_result = list()
sap_total_comp_cost_err = list()

for num in sap_total_comp_result_dict:
    result, err = mean_confidence_interval(sap_total_comp_result_dict[num], confidence=0.95)
    sap_total_comp_cost_result.append(result)
    sap_total_comp_cost_err.append(err)

sap_total_config_cost_result = list()
sap_total_config_cost_err = list()
for num in sap_total_config_cost_result_dict:
    result, err = mean_confidence_interval(sap_total_config_cost_result_dict[num], confidence=0.95)
    sap_total_config_cost_result.append(result)
    sap_total_config_cost_err.append(err)


fig = plt.figure(1)
ax1 = fig.add_subplot(111)

# flierprops = dict(marker='o', markerfacecolor='green', markersize=12,linestyle='none')
# medianprops = dict(linestyle='-.', linewidth=1.5, color='firebrick')

colors = ['darkorange', 'green', 'firebrick', 'navy', 'blue', 'purple']

# print len(sap_total_cost_result), len(sap_total_cost_err)
# markeredgewidth=2,
index = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
plt.errorbar(index, sap_total_cost_result, yerr=sap_total_cost_err, color=colors[4], linewidth=3, marker='x', markersize=15, label=r'SAP', markeredgewidth=2, capsize=3, fillstyle='none')
# plt.errorbar(index, sap_total_comp_cost_result, yerr=sap_total_comp_cost_err, color=colors[4], linewidth=3, marker='x', markersize=15, label=r'SAP', markeredgewidth=2, capsize=3, fillstyle='none')
# plt.errorbar(index, sap_total_cost_result, yerr=sap_total_cost_err, color=colors[4], linewidth=3, marker='x', markersize=15, label=r'SAP', markeredgewidth=2, capsize=3, fillstyle='none')


# plt.legend(handler_map={f1: legend_handler.HandlerErrorbar(xerr_size=5)})

plt.xticks([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],)


plt.tick_params(labelsize=12)
plt.grid(linestyle='--', linewidth=1)
# plt.xticks(range(1, LenSFC+1), range(1, LenSFC+1))

# plt.legend(numpoints=3, prop={'size': 16,'family':'Times New Roman'})

# plt.title(r'$\alpha_{max} = 3$', fontsize=16, fontname='Times New Roman')
ax1.set_xlabel(r'NS length $|F_s|_{\rm max}$', fontsize=14, fontname='Times New Roman')
ax1.set_ylabel('Total cost', fontsize=14, fontname='Times New Roman')

ax1.legend(prop={'size': 14,'family':'Times New Roman'})

plt.show()
